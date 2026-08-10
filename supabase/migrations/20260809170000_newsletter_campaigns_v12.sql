-- GUAMAISON Newsletter Campaigns v12
-- Resumable bulk campaigns, per-recipient consent checks, deduplication and RLS.

begin;

create table if not exists public.newsletter_campaigns (
  id uuid primary key default extensions.gen_random_uuid(),
  admin_user_id uuid,
  name text not null,
  subject text not null,
  body_text text not null,
  action_label text,
  action_url text,
  target_mode text not null default 'all_active',
  status text not null default 'draft',
  target_count integer not null default 0,
  pending_count integer not null default 0,
  processing_count integer not null default 0,
  sent_count integer not null default 0,
  failed_count integer not null default 0,
  skipped_count integer not null default 0,
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint newsletter_campaigns_name_length check (char_length(name) between 3 and 120),
  constraint newsletter_campaigns_subject_length check (char_length(subject) between 3 and 160),
  constraint newsletter_campaigns_body_length check (char_length(body_text) between 10 and 10000),
  constraint newsletter_campaigns_target_mode_check check (target_mode in ('all_active', 'selected')),
  constraint newsletter_campaigns_status_check check (status in ('draft', 'ready', 'sending', 'paused', 'completed', 'cancelled')),
  constraint newsletter_campaigns_action_pair_check check (
    (action_label is null and action_url is null)
    or (char_length(action_label) between 1 and 60 and char_length(action_url) between 8 and 1000)
  ),
  constraint newsletter_campaigns_counts_check check (
    target_count >= 0 and pending_count >= 0 and processing_count >= 0
    and sent_count >= 0 and failed_count >= 0 and skipped_count >= 0
  )
);

create index if not exists newsletter_campaigns_created_idx
  on public.newsletter_campaigns (created_at desc);

create index if not exists newsletter_campaigns_status_idx
  on public.newsletter_campaigns (status, created_at desc);

create table if not exists public.newsletter_campaign_recipients (
  id uuid primary key default extensions.gen_random_uuid(),
  campaign_id uuid not null references public.newsletter_campaigns(id) on delete cascade,
  subscriber_id uuid not null references public.newsletter_subscribers(id) on delete cascade,
  email text not null,
  full_name text,
  unsubscribe_token uuid,
  status text not null default 'pending',
  attempt_count integer not null default 0,
  error_message text,
  processing_started_at timestamptz,
  sent_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint newsletter_campaign_recipients_status_check check (
    status in ('pending', 'processing', 'sent', 'failed', 'skipped')
  ),
  constraint newsletter_campaign_recipients_email_length check (char_length(email) between 3 and 254),
  constraint newsletter_campaign_recipients_attempt_check check (attempt_count between 0 and 20),
  unique (campaign_id, subscriber_id)
);

create index if not exists newsletter_campaign_recipients_queue_idx
  on public.newsletter_campaign_recipients (campaign_id, status, created_at, id);

create index if not exists newsletter_campaign_recipients_sent_idx
  on public.newsletter_campaign_recipients (sent_at desc)
  where status = 'sent';

alter table public.newsletter_campaigns enable row level security;
alter table public.newsletter_campaign_recipients enable row level security;

revoke all on table public.newsletter_campaigns from anon, authenticated;
revoke all on table public.newsletter_campaign_recipients from anon, authenticated;

grant select, insert, update, delete on table public.newsletter_campaigns to service_role;
grant select, insert, update, delete on table public.newsletter_campaign_recipients to service_role;

create or replace function public.newsletter_prepare_campaign_v12(
  p_campaign_id uuid,
  p_target_mode text,
  p_subscriber_ids uuid[] default null
)
returns table (prepared_count integer)
language plpgsql
security definer
set search_path = ''
as $function$
declare
  v_count integer := 0;
begin
  if p_target_mode not in ('all_active', 'selected') then
    raise exception 'invalid campaign target mode';
  end if;

  perform 1
  from public.newsletter_campaigns as c
  where c.id = p_campaign_id and c.status = 'draft'
  for update;

  if not found then
    raise exception 'campaign is missing or no longer a draft';
  end if;

  insert into public.newsletter_campaign_recipients (
    campaign_id,
    subscriber_id,
    email,
    full_name,
    unsubscribe_token,
    status,
    created_at,
    updated_at
  )
  select
    p_campaign_id,
    s.id,
    lower(btrim(s.email)),
    nullif(btrim(coalesce(s.full_name, '')), ''),
    s.unsubscribe_token,
    'pending',
    now(),
    now()
  from public.newsletter_subscribers as s
  where s.status = 'active'
    and s.unsubscribe_token is not null
    and (
      p_target_mode = 'all_active'
      or (p_target_mode = 'selected' and s.id = any(coalesce(p_subscriber_ids, array[]::uuid[])))
    )
  on conflict (campaign_id, subscriber_id) do nothing;

  get diagnostics v_count = row_count;

  update public.newsletter_campaigns
  set
    target_mode = p_target_mode,
    status = 'ready',
    target_count = v_count,
    pending_count = v_count,
    processing_count = 0,
    sent_count = 0,
    failed_count = 0,
    skipped_count = 0,
    updated_at = now()
  where id = p_campaign_id;

  return query select v_count;
end;
$function$;

create or replace function public.newsletter_claim_campaign_batch_v12(
  p_campaign_id uuid,
  p_limit integer default 10
)
returns table (
  id uuid,
  campaign_id uuid,
  subscriber_id uuid,
  email text,
  full_name text,
  unsubscribe_token uuid,
  status text,
  attempt_count integer,
  error_message text,
  sent_at timestamptz,
  created_at timestamptz
)
language plpgsql
security definer
set search_path = ''
as $function$
begin
  if not exists (
    select 1 from public.newsletter_campaigns as c
    where c.id = p_campaign_id and c.status = 'sending'
  ) then
    return;
  end if;

  update public.newsletter_campaign_recipients as r
  set
    status = 'pending',
    processing_started_at = null,
    updated_at = now()
  where r.campaign_id = p_campaign_id
    and r.status = 'processing'
    and r.processing_started_at < now() - interval '15 minutes';

  update public.newsletter_campaign_recipients as r
  set
    status = 'skipped',
    error_message = 'Đã hủy nhận tin trước khi chiến dịch gửi.',
    updated_at = now()
  where r.campaign_id = p_campaign_id
    and r.status = 'pending'
    and not exists (
      select 1
      from public.newsletter_subscribers as s
      where s.id = r.subscriber_id
        and s.status = 'active'
        and s.unsubscribe_token is not null
    );

  return query
  with candidates as (
    select r.id
    from public.newsletter_campaign_recipients as r
    join public.newsletter_subscribers as s on s.id = r.subscriber_id
    where r.campaign_id = p_campaign_id
      and r.status = 'pending'
      and r.attempt_count < 20
      and s.status = 'active'
      and s.unsubscribe_token is not null
    order by r.created_at, r.id
    for update of r skip locked
    limit least(25, greatest(1, coalesce(p_limit, 10)))
  ), updated as (
    update public.newsletter_campaign_recipients as r
    set
      status = 'processing',
      attempt_count = r.attempt_count + 1,
      processing_started_at = now(),
      error_message = null,
      updated_at = now()
    from candidates as c
    where r.id = c.id
    returning r.*
  )
  select
    u.id,
    u.campaign_id,
    u.subscriber_id,
    s.email,
    coalesce(s.full_name, ''),
    s.unsubscribe_token,
    u.status,
    u.attempt_count,
    u.error_message,
    u.sent_at,
    u.created_at
  from updated as u
  join public.newsletter_subscribers as s on s.id = u.subscriber_id
  order by u.created_at, u.id;
end;
$function$;

create or replace function public.newsletter_refresh_campaign_v12(p_campaign_id uuid)
returns setof public.newsletter_campaigns
language plpgsql
security definer
set search_path = ''
as $function$
declare
  v_pending integer := 0;
  v_processing integer := 0;
  v_sent integer := 0;
  v_failed integer := 0;
  v_skipped integer := 0;
  v_total integer := 0;
begin
  select
    count(*)::integer,
    count(*) filter (where status = 'pending')::integer,
    count(*) filter (where status = 'processing')::integer,
    count(*) filter (where status = 'sent')::integer,
    count(*) filter (where status = 'failed')::integer,
    count(*) filter (where status = 'skipped')::integer
  into v_total, v_pending, v_processing, v_sent, v_failed, v_skipped
  from public.newsletter_campaign_recipients
  where campaign_id = p_campaign_id;

  update public.newsletter_campaigns as c
  set
    target_count = v_total,
    pending_count = v_pending,
    processing_count = v_processing,
    sent_count = v_sent,
    failed_count = v_failed,
    skipped_count = v_skipped,
    status = case
      when c.status = 'cancelled' then 'cancelled'
      when v_pending = 0 and v_processing = 0 then 'completed'
      else c.status
    end,
    completed_at = case
      when c.status <> 'cancelled' and v_pending = 0 and v_processing = 0
        then coalesce(c.completed_at, now())
      else c.completed_at
    end,
    updated_at = now()
  where c.id = p_campaign_id;

  return query select c.* from public.newsletter_campaigns as c where c.id = p_campaign_id;
end;
$function$;

create or replace function public.newsletter_retry_failed_v12(p_campaign_id uuid)
returns table (queued_count integer)
language plpgsql
security definer
set search_path = ''
as $function$
declare
  v_count integer := 0;
begin
  update public.newsletter_campaign_recipients
  set
    status = 'pending',
    error_message = null,
    processing_started_at = null,
    updated_at = now()
  where campaign_id = p_campaign_id
    and status = 'failed'
    and attempt_count < 20;

  get diagnostics v_count = row_count;

  update public.newsletter_campaigns
  set status = 'ready', completed_at = null, updated_at = now()
  where id = p_campaign_id and status <> 'cancelled';

  perform public.newsletter_refresh_campaign_v12(p_campaign_id);
  return query select v_count;
end;
$function$;

create or replace function public.newsletter_cancel_campaign_v12(p_campaign_id uuid)
returns table (cancelled_count integer)
language plpgsql
security definer
set search_path = ''
as $function$
declare
  v_count integer := 0;
begin
  update public.newsletter_campaign_recipients
  set
    status = 'skipped',
    error_message = 'Chiến dịch đã bị Admin hủy.',
    processing_started_at = null,
    updated_at = now()
  where campaign_id = p_campaign_id
    and (
      status in ('pending', 'failed')
      or (status = 'processing' and processing_started_at < now() - interval '15 minutes')
    );

  get diagnostics v_count = row_count;

  update public.newsletter_campaigns
  set status = 'cancelled', completed_at = now(), updated_at = now()
  where id = p_campaign_id and status <> 'completed';

  perform public.newsletter_refresh_campaign_v12(p_campaign_id);
  return query select v_count;
end;
$function$;

revoke all on function public.newsletter_prepare_campaign_v12(uuid, text, uuid[]) from public, anon, authenticated;
revoke all on function public.newsletter_claim_campaign_batch_v12(uuid, integer) from public, anon, authenticated;
revoke all on function public.newsletter_refresh_campaign_v12(uuid) from public, anon, authenticated;
revoke all on function public.newsletter_retry_failed_v12(uuid) from public, anon, authenticated;
revoke all on function public.newsletter_cancel_campaign_v12(uuid) from public, anon, authenticated;

grant execute on function public.newsletter_prepare_campaign_v12(uuid, text, uuid[]) to service_role;
grant execute on function public.newsletter_claim_campaign_batch_v12(uuid, integer) to service_role;
grant execute on function public.newsletter_refresh_campaign_v12(uuid) to service_role;
grant execute on function public.newsletter_retry_failed_v12(uuid) to service_role;
grant execute on function public.newsletter_cancel_campaign_v12(uuid) to service_role;

comment on table public.newsletter_campaigns is
  'GUAMAISON Admin newsletter campaigns with resumable aggregate status.';
comment on table public.newsletter_campaign_recipients is
  'Per-subscriber delivery queue. Unique per campaign and rechecked against active consent before claim.';

commit;

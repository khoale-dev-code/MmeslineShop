-- GUAMAISON Newsletter v11
-- Durable opt-in records, Admin inbox, email history, RLS and atomic RPCs.

begin;

create schema if not exists extensions;
create extension if not exists pgcrypto with schema extensions;

create table if not exists public.newsletter_subscribers (
  id uuid primary key default gen_random_uuid(),
  email text not null,
  full_name text,
  status text not null default 'active',
  source text not null default 'storefront',
  locale text not null default 'vi',
  consent_version text not null,
  consented_at timestamptz not null default now(),
  last_subscribed_at timestamptz not null default now(),
  unsubscribed_at timestamptz,
  last_viewed_at timestamptz,
  last_replied_at timestamptz,
  is_unread boolean not null default true,
  unsubscribe_token uuid not null default gen_random_uuid(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint newsletter_subscribers_email_length check (char_length(email) between 3 and 254),
  constraint newsletter_subscribers_status_check check (status in ('active', 'unsubscribed', 'blocked'))
);

create unique index if not exists newsletter_subscribers_email_lower_uidx
  on public.newsletter_subscribers (lower(btrim(email)));

create unique index if not exists newsletter_subscribers_unsubscribe_token_uidx
  on public.newsletter_subscribers (unsubscribe_token);

create index if not exists newsletter_subscribers_admin_inbox_idx
  on public.newsletter_subscribers (is_unread desc, created_at desc);

create index if not exists newsletter_subscribers_status_idx
  on public.newsletter_subscribers (status, created_at desc);

create table if not exists public.newsletter_messages (
  id uuid primary key default gen_random_uuid(),
  subscriber_id uuid not null references public.newsletter_subscribers(id) on delete cascade,
  admin_user_id uuid,
  subject text not null,
  body_text text not null,
  status text not null default 'processing',
  error_message text,
  sent_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint newsletter_messages_subject_length check (char_length(subject) between 3 and 160),
  constraint newsletter_messages_body_length check (char_length(body_text) between 10 and 10000),
  constraint newsletter_messages_status_check check (status in ('processing', 'sent', 'failed'))
);

create index if not exists newsletter_messages_subscriber_idx
  on public.newsletter_messages (subscriber_id, created_at desc);

create index if not exists newsletter_messages_status_idx
  on public.newsletter_messages (status, created_at desc);

create table if not exists public.newsletter_rate_limits (
  fingerprint text primary key,
  window_started_at timestamptz not null default now(),
  request_count integer not null default 1,
  updated_at timestamptz not null default now(),
  constraint newsletter_rate_limits_count_check check (request_count >= 1)
);

create index if not exists newsletter_rate_limits_window_idx
  on public.newsletter_rate_limits (window_started_at);

alter table public.newsletter_subscribers enable row level security;
alter table public.newsletter_messages enable row level security;
alter table public.newsletter_rate_limits enable row level security;

revoke all on table public.newsletter_subscribers from anon, authenticated;
revoke all on table public.newsletter_messages from anon, authenticated;
revoke all on table public.newsletter_rate_limits from anon, authenticated;

grant select, insert, update, delete on table public.newsletter_subscribers to service_role;
grant select, insert, update, delete on table public.newsletter_messages to service_role;
grant select, insert, update, delete on table public.newsletter_rate_limits to service_role;

create or replace function public.newsletter_subscribe_v11(
  p_email text,
  p_full_name text default null,
  p_source text default 'storefront',
  p_locale text default 'vi',
  p_consent_version text default 'newsletter-v11',
  p_fingerprint text default null
)
returns table (
  subscription_id uuid,
  result_code text,
  subscription_status text,
  unsubscribe_token uuid
)
language plpgsql
security definer
set search_path = ''
as $function$
declare
  v_email text := lower(btrim(coalesce(p_email, '')));
  v_name text := nullif(btrim(coalesce(p_full_name, '')), '');
  v_source text := left(coalesce(nullif(btrim(p_source), ''), 'storefront'), 80);
  v_locale text := left(coalesce(nullif(btrim(p_locale), ''), 'vi'), 12);
  v_consent text := left(coalesce(nullif(btrim(p_consent_version), ''), 'newsletter-v11'), 80);
  v_now timestamptz := now();
  v_request_count integer := 1;
  v_row public.newsletter_subscribers%rowtype;
begin
  if char_length(v_email) < 3
     or char_length(v_email) > 254
     or position('@' in v_email) < 2
     or position('.' in split_part(v_email, '@', 2)) < 2 then
    return query select null::uuid, 'invalid_email'::text, null::text, null::uuid;
    return;
  end if;

  if p_fingerprint is not null and char_length(btrim(p_fingerprint)) between 32 and 128 then
    insert into public.newsletter_rate_limits (
      fingerprint,
      window_started_at,
      request_count,
      updated_at
    )
    values (
      left(btrim(p_fingerprint), 128),
      v_now,
      1,
      v_now
    )
    on conflict (fingerprint) do update
    set
      window_started_at = case
        when public.newsletter_rate_limits.window_started_at < v_now - interval '10 minutes'
          then v_now
        else public.newsletter_rate_limits.window_started_at
      end,
      request_count = case
        when public.newsletter_rate_limits.window_started_at < v_now - interval '10 minutes'
          then 1
        else public.newsletter_rate_limits.request_count + 1
      end,
      updated_at = v_now
    returning request_count into v_request_count;

    if v_request_count > 8 then
      return query select null::uuid, 'rate_limited'::text, null::text, null::uuid;
      return;
    end if;
  end if;

  select ns.*
    into v_row
  from public.newsletter_subscribers as ns
  where lower(btrim(ns.email)) = v_email
  for update;

  if found then
    if v_row.status = 'blocked' then
      return query select v_row.id, 'blocked'::text, v_row.status, v_row.unsubscribe_token;
      return;
    end if;

    if v_row.status = 'active' then
      update public.newsletter_subscribers
      set
        full_name = coalesce(v_name, full_name),
        source = v_source,
        locale = v_locale,
        last_subscribed_at = v_now,
        updated_at = v_now
      where id = v_row.id
      returning * into v_row;

      return query select v_row.id, 'already_active'::text, v_row.status, v_row.unsubscribe_token;
      return;
    end if;

    update public.newsletter_subscribers
    set
      email = v_email,
      full_name = coalesce(v_name, full_name),
      status = 'active',
      source = v_source,
      locale = v_locale,
      consent_version = v_consent,
      consented_at = v_now,
      last_subscribed_at = v_now,
      unsubscribed_at = null,
      is_unread = true,
      unsubscribe_token = gen_random_uuid(),
      updated_at = v_now
    where id = v_row.id
    returning * into v_row;

    return query select v_row.id, 'reactivated'::text, v_row.status, v_row.unsubscribe_token;
    return;
  end if;

  insert into public.newsletter_subscribers (
    email,
    full_name,
    status,
    source,
    locale,
    consent_version,
    consented_at,
    last_subscribed_at,
    is_unread,
    created_at,
    updated_at
  )
  values (
    v_email,
    v_name,
    'active',
    v_source,
    v_locale,
    v_consent,
    v_now,
    v_now,
    true,
    v_now,
    v_now
  )
  returning * into v_row;

  return query select v_row.id, 'created'::text, v_row.status, v_row.unsubscribe_token;
end;
$function$;

create or replace function public.newsletter_unsubscribe_v11(p_token uuid)
returns table (unsubscribed boolean)
language plpgsql
security definer
set search_path = ''
as $function$
declare
  v_updated integer := 0;
begin
  update public.newsletter_subscribers
  set
    status = 'unsubscribed',
    unsubscribed_at = now(),
    is_unread = false,
    updated_at = now()
  where unsubscribe_token = p_token
    and status <> 'blocked';

  get diagnostics v_updated = row_count;
  return query select (v_updated > 0);
end;
$function$;

revoke all on function public.newsletter_subscribe_v11(text, text, text, text, text, text)
  from public, anon, authenticated;
revoke all on function public.newsletter_unsubscribe_v11(uuid)
  from public, anon, authenticated;

grant execute on function public.newsletter_subscribe_v11(text, text, text, text, text, text)
  to service_role;
grant execute on function public.newsletter_unsubscribe_v11(uuid)
  to service_role;

comment on table public.newsletter_subscribers is
  'GUAMAISON newsletter opt-ins. Server-side service_role only; no public table access.';
comment on table public.newsletter_messages is
  'One-to-one Admin email history for newsletter subscribers.';

commit;

-- GUAMAISON Contact Center v13
-- Run once in Supabase SQL Editor after installing the application package.

create extension if not exists pgcrypto;

create table if not exists public.contact_page_settings (
  id text primary key default 'primary',
  eyebrow text not null default 'Customer care · GUAMAISON',
  title text not null default 'Kết nối cùng',
  accent_text text not null default 'GUAMAISON',
  description text not null default 'Cần tư vấn sản phẩm, hỗ trợ đơn hàng hay muốn hợp tác cùng chúng tôi? Hãy để lại lời nhắn, đội ngũ GUAMAISON sẽ phản hồi sớm nhất.',
  form_eyebrow text not null default 'Gửi lời nhắn',
  form_title text not null default 'Chúng tôi luôn lắng nghe.',
  form_description text not null default 'Điền thông tin bên dưới. GUAMAISON sẽ liên hệ qua email hoặc số điện thoại bạn cung cấp.',
  map_title text not null default 'GUAMAISON Studio',
  address text not null default 'TP. Hồ Chí Minh, Việt Nam',
  contact_email text not null default 'support@guamaison.vn',
  contact_phone text not null default '+84 90 123 4567',
  business_hours text not null default '09:00 – 21:00 · Thứ Hai – Chủ Nhật',
  response_note text not null default 'Phản hồi dự kiến trong vòng 24 giờ làm việc.',
  map_embed_url text not null default '',
  directions_url text not null default 'https://www.google.com/maps',
  theme text not null default 'ink',
  topics jsonb not null default '["Hỗ trợ đơn hàng","Tư vấn sản phẩm","Đổi trả / bảo hành","Hợp tác thương mại","Góp ý thương hiệu","Khác"]'::jsonb,
  updated_by uuid null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint contact_page_settings_singleton check (id = 'primary'),
  constraint contact_page_settings_theme check (theme in ('ink', 'rose', 'espresso')),
  constraint contact_page_settings_topics_array check (jsonb_typeof(topics) = 'array')
);

insert into public.contact_page_settings (id)
values ('primary')
on conflict (id) do nothing;

create table if not exists public.contact_messages (
  id uuid primary key default gen_random_uuid(),
  full_name text not null,
  email text not null,
  phone text not null default '',
  topic text not null default 'Khác',
  message text not null,
  status text not null default 'new',
  is_unread boolean not null default true,
  admin_note text not null default '',
  request_fingerprint text not null,
  last_viewed_at timestamptz null,
  replied_at timestamptz null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint contact_messages_status check (status in ('new', 'open', 'replied', 'closed', 'spam')),
  constraint contact_messages_email_length check (char_length(email) between 3 and 254),
  constraint contact_messages_name_length check (char_length(full_name) between 2 and 100),
  constraint contact_messages_body_length check (char_length(message) between 10 and 4000),
  constraint contact_messages_fingerprint_length check (char_length(request_fingerprint) = 64)
);

create table if not exists public.contact_replies (
  id uuid primary key default gen_random_uuid(),
  contact_message_id uuid not null references public.contact_messages(id) on delete cascade,
  admin_user_id uuid null,
  subject text not null,
  body_text text not null,
  status text not null default 'processing',
  error_message text null,
  created_at timestamptz not null default now(),
  sent_at timestamptz null,
  updated_at timestamptz not null default now(),
  constraint contact_replies_status check (status in ('processing', 'sent', 'failed')),
  constraint contact_replies_subject_length check (char_length(subject) between 1 and 160),
  constraint contact_replies_body_length check (char_length(body_text) between 1 and 8000)
);

create index if not exists contact_messages_created_idx
  on public.contact_messages (created_at desc);
create index if not exists contact_messages_unread_idx
  on public.contact_messages (is_unread, created_at desc);
create index if not exists contact_messages_status_idx
  on public.contact_messages (status, created_at desc);
create index if not exists contact_messages_email_idx
  on public.contact_messages (lower(email));
create index if not exists contact_messages_fingerprint_idx
  on public.contact_messages (request_fingerprint, created_at desc);
create index if not exists contact_replies_message_idx
  on public.contact_replies (contact_message_id, created_at desc);

create or replace function public.contact_touch_updated_at_v13()
returns trigger
language plpgsql
set search_path = public, pg_temp
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists contact_page_settings_touch_v13 on public.contact_page_settings;
create trigger contact_page_settings_touch_v13
before update on public.contact_page_settings
for each row execute function public.contact_touch_updated_at_v13();

drop trigger if exists contact_messages_touch_v13 on public.contact_messages;
create trigger contact_messages_touch_v13
before update on public.contact_messages
for each row execute function public.contact_touch_updated_at_v13();

drop trigger if exists contact_replies_touch_v13 on public.contact_replies;
create trigger contact_replies_touch_v13
before update on public.contact_replies
for each row execute function public.contact_touch_updated_at_v13();

create or replace function public.contact_submit_message_v13(
  p_full_name text,
  p_email text,
  p_phone text,
  p_topic text,
  p_message text,
  p_fingerprint text
)
returns table(result_code text, contact_message_id uuid)
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_id uuid;
  v_recent_count integer;
begin
  if char_length(trim(coalesce(p_full_name, ''))) not between 2 and 100
     or char_length(trim(coalesce(p_email, ''))) not between 3 and 254
     or position('@' in coalesce(p_email, '')) < 2
     or char_length(trim(coalesce(p_message, ''))) not between 10 and 4000
     or char_length(coalesce(p_fingerprint, '')) <> 64 then
    return query select 'invalid'::text, null::uuid;
    return;
  end if;

  perform pg_advisory_xact_lock(hashtextextended(p_fingerprint, 13));

  select count(*)::integer
    into v_recent_count
    from public.contact_messages
   where request_fingerprint = p_fingerprint
     and created_at >= now() - interval '60 minutes';

  if v_recent_count >= 5 then
    return query select 'rate_limited'::text, null::uuid;
    return;
  end if;

  insert into public.contact_messages (
    full_name,
    email,
    phone,
    topic,
    message,
    request_fingerprint
  ) values (
    left(trim(p_full_name), 100),
    lower(left(trim(p_email), 254)),
    left(trim(coalesce(p_phone, '')), 30),
    left(coalesce(nullif(trim(p_topic), ''), 'Khác'), 80),
    left(trim(p_message), 4000),
    p_fingerprint
  )
  returning id into v_id;

  return query select 'created'::text, v_id;
end;
$$;

alter table public.contact_page_settings enable row level security;
alter table public.contact_messages enable row level security;
alter table public.contact_replies enable row level security;

drop policy if exists contact_page_settings_service_role_v13 on public.contact_page_settings;
create policy contact_page_settings_service_role_v13
on public.contact_page_settings for all to service_role
using (true) with check (true);

drop policy if exists contact_messages_service_role_v13 on public.contact_messages;
create policy contact_messages_service_role_v13
on public.contact_messages for all to service_role
using (true) with check (true);

drop policy if exists contact_replies_service_role_v13 on public.contact_replies;
create policy contact_replies_service_role_v13
on public.contact_replies for all to service_role
using (true) with check (true);

revoke all on table public.contact_page_settings from anon, authenticated;
revoke all on table public.contact_messages from anon, authenticated;
revoke all on table public.contact_replies from anon, authenticated;
grant select, insert, update, delete on table public.contact_page_settings to service_role;
grant select, insert, update, delete on table public.contact_messages to service_role;
grant select, insert, update, delete on table public.contact_replies to service_role;

revoke all on function public.contact_submit_message_v13(text, text, text, text, text, text) from public, anon, authenticated;
grant execute on function public.contact_submit_message_v13(text, text, text, text, text, text) to service_role;
revoke all on function public.contact_touch_updated_at_v13() from public, anon, authenticated;
grant execute on function public.contact_touch_updated_at_v13() to service_role;

comment on table public.contact_messages is
  'Private contact requests. A contact request never creates marketing consent.';
comment on function public.contact_submit_message_v13(text, text, text, text, text, text) is
  'Service-role-only contact submission with a five-messages-per-hour fingerprint limit.';

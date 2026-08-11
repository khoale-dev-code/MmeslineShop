-- GUAMAISON v18 · Shared Admin Action Inbox
-- Idempotent migration: event table, RLS, counters, event capture and 30-day backfill.

begin;

create extension if not exists pgcrypto;

create table if not exists public.admin_events (
  id uuid primary key default gen_random_uuid(),
  event_key text not null unique,
  event_type text not null,
  category text not null,
  priority text not null default 'normal',
  title text not null,
  message text not null default '',
  entity_type text not null default '',
  entity_id text not null default '',
  action_url text not null default '/admin/notifications',
  action_label text not null default 'Xem chi tiết',
  actor_id uuid null,
  actor_name text not null default '',
  actor_email text not null default '',
  metadata jsonb not null default '{}'::jsonb,
  status text not null default 'unread',
  occurred_at timestamptz not null default now(),
  read_at timestamptz null,
  read_by uuid null,
  resolved_at timestamptz null,
  resolved_by uuid null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint admin_events_category_v18 check (category in ('order','payment','return','contact','marketing','system')),
  constraint admin_events_priority_v18 check (priority in ('info','normal','high','urgent')),
  constraint admin_events_status_v18 check (status in ('unread','read','resolved')),
  constraint admin_events_action_url_v18 check (action_url like '/admin/%'),
  constraint admin_events_title_v18 check (char_length(title) between 1 and 180),
  constraint admin_events_message_v18 check (char_length(message) <= 1000)
);

create index if not exists admin_events_inbox_v18_idx
  on public.admin_events (status, priority, occurred_at desc);
create index if not exists admin_events_category_v18_idx
  on public.admin_events (category, occurred_at desc);
create index if not exists admin_events_entity_v18_idx
  on public.admin_events (entity_type, entity_id);

alter table public.admin_events enable row level security;
revoke all on table public.admin_events from anon, authenticated;
grant select, insert, update, delete on table public.admin_events to service_role;

drop policy if exists admin_events_service_role_v18 on public.admin_events;
create policy admin_events_service_role_v18
on public.admin_events for all to service_role
using (true) with check (true);

create or replace function public.admin_event_emit_v18(
  p_event_key text,
  p_event_type text,
  p_category text,
  p_priority text,
  p_title text,
  p_message text,
  p_entity_type text,
  p_entity_id text,
  p_action_url text,
  p_action_label text,
  p_actor_id uuid default null,
  p_actor_name text default '',
  p_actor_email text default '',
  p_metadata jsonb default '{}'::jsonb,
  p_occurred_at timestamptz default now()
)
returns uuid
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_id uuid;
begin
  insert into public.admin_events (
    event_key,event_type,category,priority,title,message,entity_type,entity_id,
    action_url,action_label,actor_id,actor_name,actor_email,metadata,occurred_at
  ) values (
    left(p_event_key,240),left(p_event_type,80),p_category,p_priority,left(p_title,180),left(coalesce(p_message,''),1000),
    left(coalesce(p_entity_type,''),80),left(coalesce(p_entity_id,''),120),left(p_action_url,500),left(p_action_label,80),
    p_actor_id,left(coalesce(p_actor_name,''),160),left(coalesce(p_actor_email,''),254),coalesce(p_metadata,'{}'::jsonb),coalesce(p_occurred_at,now())
  )
  on conflict (event_key) do nothing
  returning id into v_id;

  if v_id is null then
    select id into v_id from public.admin_events where event_key = left(p_event_key,240);
  end if;
  return v_id;
end;
$$;

create or replace function public.admin_event_capture_v18()
returns trigger
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_new jsonb := to_jsonb(new);
  v_old jsonb := case when tg_op = 'UPDATE' then to_jsonb(old) else '{}'::jsonb end;
  v_id text := coalesce(v_new->>'id','');
  v_user_id uuid;
  v_actor_name text := '';
  v_actor_email text := '';
  v_code text;
  v_amount numeric;
  v_status text;
begin
  begin v_user_id := nullif(v_new->>'user_id','')::uuid; exception when others then v_user_id := null; end;
  if v_user_id is not null and to_regclass('public.users') is not null then
    select coalesce(u.full_name,''),coalesce(u.email,'') into v_actor_name,v_actor_email
    from public.users u where u.id = v_user_id limit 1;
  end if;

  if tg_table_name = 'orders' then
    if upper(coalesce(nullif(v_new->>'sales_channel',''),nullif(v_new->>'source',''),'WEB')) in ('POS','STORE','OFFLINE') then
      return new;
    end if;
    v_code := coalesce(nullif(v_new->>'code',''),upper(left(v_id,8)));
    v_actor_name := coalesce(nullif(v_new->>'customer_name',''),nullif(v_actor_name,''),'Khách hàng');
    begin v_amount := coalesce((v_new->>'total_amount')::numeric,0); exception when others then v_amount := 0; end;

    if tg_op = 'INSERT' then
      perform public.admin_event_emit_v18(
        'order:created:'||v_id,'order.created','order','high',
        'Đơn hàng mới #'||v_code,
        v_actor_name||' vừa đặt đơn trị giá '||to_char(v_amount,'FM999G999G999G990')||'đ. Kiểm tra thanh toán và chuẩn bị xử lý đơn.',
        'order',v_id,'/admin/orders/'||v_id,'Xem đơn hàng',v_user_id,v_actor_name,v_actor_email,
        jsonb_build_object('order_code',v_code,'amount',v_amount,'payment_method',v_new->>'payment_method'),
        coalesce(nullif(v_new->>'created_at','')::timestamptz,now())
      );
    elsif tg_op = 'UPDATE' then
      if coalesce(v_old->>'payment_status','') is distinct from coalesce(v_new->>'payment_status','') then
        v_status := coalesce(v_new->>'payment_status','');
        if v_status in ('paid','failed') and coalesce(v_new->>'transaction_id','') not like 'MANUAL_ADMIN_%' then
          perform public.admin_event_emit_v18(
            'order:payment:'||v_id||':'||v_status,'order.payment_'||v_status,'payment',case when v_status='failed' then 'urgent' else 'normal' end,
            case when v_status='paid' then 'Đã nhận thanh toán #'||v_code else 'Thanh toán thất bại #'||v_code end,
            case when v_status='paid' then 'Hệ thống đã xác nhận thanh toán. Đơn hàng có thể chuyển sang bước xử lý tiếp theo.' else 'Thanh toán của khách chưa thành công. Kiểm tra giao dịch trước khi xử lý đơn.' end,
            'order',v_id,'/admin/orders/'||v_id,'Kiểm tra đơn',v_user_id,v_actor_name,v_actor_email,
            jsonb_build_object('order_code',v_code,'amount',v_amount,'payment_status',v_status,'transaction_id',v_new->>'transaction_id'),now()
          );
        end if;
      end if;
      if coalesce(v_old->>'status','') is distinct from coalesce(v_new->>'status','') and v_new->>'status' = 'cancelled' then
        perform public.admin_event_emit_v18(
          'order:cancelled:'||v_id,'order.cancelled','order','high','Khách đã hủy đơn #'||v_code,
          v_actor_name||' vừa hủy đơn khi đơn còn chờ xử lý. Kiểm tra tồn kho và lịch sử thanh toán nếu cần.',
          'order',v_id,'/admin/orders/'||v_id,'Xem đơn đã hủy',v_user_id,v_actor_name,v_actor_email,
          jsonb_build_object('order_code',v_code,'amount',v_amount,'previous_status',v_old->>'status'),now()
        );
      end if;
    end if;

  elsif tg_table_name = 'return_requests' and tg_op = 'INSERT' then
    perform public.admin_event_emit_v18(
      'return:requested:'||v_id,'return.requested','return','urgent',
      'Yêu cầu đổi / trả hàng mới',
      coalesce(nullif(v_actor_name,''),'Khách hàng')||' vừa gửi yêu cầu đổi / trả. Cần kiểm tra lý do và phản hồi trong thời gian cam kết.',
      'return_request',v_id,'/admin/returns/'||v_id,'Xử lý yêu cầu',v_user_id,v_actor_name,v_actor_email,
      jsonb_build_object('order_id',v_new->>'order_id','reason',left(coalesce(v_new->>'reason',''),300)),
      coalesce(nullif(v_new->>'requested_at','')::timestamptz,now())
    );

  elsif tg_table_name = 'contact_messages' and tg_op = 'INSERT' then
    perform public.admin_event_emit_v18(
      'contact:created:'||v_id,'contact.created','contact','high',
      'Tin nhắn liên hệ mới · '||coalesce(nullif(v_new->>'topic',''),'Khác'),
      coalesce(nullif(v_new->>'full_name',''),'Khách hàng')||' vừa gửi lời nhắn. Mở hộp thư để đọc và phản hồi.',
      'contact_message',v_id,'/admin/newsletter/messages/'||v_id,'Đọc tin nhắn',null,
      coalesce(v_new->>'full_name',''),coalesce(v_new->>'email',''),
      jsonb_build_object('topic',v_new->>'topic','phone',v_new->>'phone'),
      coalesce(nullif(v_new->>'created_at','')::timestamptz,now())
    );

  elsif tg_table_name = 'newsletter_subscribers' then
    if tg_op = 'INSERT' or (tg_op = 'UPDATE' and coalesce(v_old->>'status','') <> 'active' and v_new->>'status' = 'active') then
      perform public.admin_event_emit_v18(
        'newsletter:'||case when tg_op='INSERT' then 'created:' else 'reactivated:' end||v_id,
        case when tg_op='INSERT' then 'newsletter.subscribed' else 'newsletter.reactivated' end,
        'marketing','info',
        case when tg_op='INSERT' then 'Có người đăng ký newsletter' else 'Khách đăng ký lại newsletter' end,
        coalesce(nullif(v_new->>'full_name',''),v_new->>'email','Khách hàng')||' đã đồng ý nhận bản tin GUAMAISON.',
        'newsletter_subscriber',v_id,'/admin/newsletter/'||v_id,'Xem người đăng ký',null,
        coalesce(v_new->>'full_name',''),coalesce(v_new->>'email',''),
        jsonb_build_object('source',v_new->>'source','status',v_new->>'status'),
        coalesce(nullif(v_new->>'last_subscribed_at','')::timestamptz,now())
      );
    end if;
  end if;
  return new;
exception when others then
  raise warning '[admin_event_capture_v18] source=%, operation=%, id=%, error=%',
    tg_table_name, tg_op, v_id, sqlerrm;
  return new;
end;
$$;

drop trigger if exists admin_event_orders_v18 on public.orders;
create trigger admin_event_orders_v18 after insert or update of payment_status, status on public.orders
for each row execute function public.admin_event_capture_v18();

drop trigger if exists admin_event_returns_v18 on public.return_requests;
create trigger admin_event_returns_v18 after insert on public.return_requests
for each row execute function public.admin_event_capture_v18();

do $$ begin
  if to_regclass('public.contact_messages') is not null then
    execute 'drop trigger if exists admin_event_contact_v18 on public.contact_messages';
    execute 'create trigger admin_event_contact_v18 after insert on public.contact_messages for each row execute function public.admin_event_capture_v18()';
  end if;
  if to_regclass('public.newsletter_subscribers') is not null then
    execute 'drop trigger if exists admin_event_newsletter_v18 on public.newsletter_subscribers';
    execute 'create trigger admin_event_newsletter_v18 after insert or update of status on public.newsletter_subscribers for each row execute function public.admin_event_capture_v18()';
  end if;
end $$;

create or replace function public.admin_event_unread_count_v18()
returns integer
language sql
stable
security definer
set search_path = public, pg_temp
as $$ select count(*)::integer from public.admin_events where status = 'unread'; $$;

create or replace function public.admin_event_stats_v18()
returns table(unread integer, high_priority integer, open_work integer, resolved_today integer, total integer)
language sql
stable
security definer
set search_path = public, pg_temp
as $$
  select
    count(*) filter (where status='unread')::integer,
    count(*) filter (where status<>'resolved' and priority in ('high','urgent'))::integer,
    count(*) filter (where status<>'resolved')::integer,
    count(*) filter (where status='resolved' and resolved_at >= date_trunc('day',now()))::integer,
    count(*)::integer
  from public.admin_events;
$$;

create or replace function public.admin_event_mark_all_read_v18(p_admin_user_id uuid default null)
returns integer
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare v_count integer;
begin
  update public.admin_events
     set status='read',read_at=now(),read_by=p_admin_user_id,updated_at=now()
   where status='unread';
  get diagnostics v_count = row_count;
  return v_count;
end;
$$;

revoke all on function public.admin_event_emit_v18(text,text,text,text,text,text,text,text,text,text,uuid,text,text,jsonb,timestamptz) from public, anon, authenticated;
revoke all on function public.admin_event_capture_v18() from public, anon, authenticated;
revoke all on function public.admin_event_unread_count_v18() from public, anon, authenticated;
revoke all on function public.admin_event_stats_v18() from public, anon, authenticated;
revoke all on function public.admin_event_mark_all_read_v18(uuid) from public, anon, authenticated;
grant execute on function public.admin_event_unread_count_v18() to service_role;
grant execute on function public.admin_event_stats_v18() to service_role;
grant execute on function public.admin_event_mark_all_read_v18(uuid) to service_role;

-- Backfill actionable records from the last 30 days. Unique event_key keeps reruns safe.
do $$
declare r record; v jsonb; v_id text; v_code text; v_amount numeric;
begin
  for r in execute 'select to_jsonb(o) as row_data from public.orders o where o.created_at >= now() - interval ''30 days'' and coalesce(to_jsonb(o)->>''status'',''pending'') in (''pending'',''confirmed'',''processing'',''packed'') and upper(coalesce(to_jsonb(o)->>''sales_channel'',to_jsonb(o)->>''source'',''WEB'')) not in (''POS'',''STORE'',''OFFLINE'')' loop
    v := r.row_data; v_id := v->>'id'; v_code := coalesce(nullif(v->>'code',''),upper(left(v_id,8)));
    begin v_amount := coalesce((v->>'total_amount')::numeric,0); exception when others then v_amount := 0; end;
    perform public.admin_event_emit_v18('order:created:'||v_id,'order.created','order','high','Đơn hàng mới #'||v_code,
      coalesce(nullif(v->>'customer_name',''),'Khách hàng')||' đã đặt đơn trị giá '||to_char(v_amount,'FM999G999G999G990')||'đ.',
      'order',v_id,'/admin/orders/'||v_id,'Xem đơn hàng',null,coalesce(v->>'customer_name',''),'',
      jsonb_build_object('order_code',v_code,'amount',v_amount,'backfilled',true),coalesce(nullif(v->>'created_at','')::timestamptz,now()));
  end loop;

  for r in execute 'select to_jsonb(x) as row_data from public.return_requests x where x.status in (''pending'',''approved'') and x.requested_at >= now() - interval ''30 days''' loop
    v := r.row_data; v_id := v->>'id';
    perform public.admin_event_emit_v18('return:requested:'||v_id,'return.requested','return','urgent','Yêu cầu đổi / trả hàng cần xử lý',
      'Khách hàng đã gửi yêu cầu đổi / trả cho đơn '||upper(left(coalesce(v->>'order_id',''),8))||'.',
      'return_request',v_id,'/admin/returns/'||v_id,'Xử lý yêu cầu',null,'','',
      jsonb_build_object('order_id',v->>'order_id','backfilled',true),coalesce(nullif(v->>'requested_at','')::timestamptz,now()));
  end loop;

  if to_regclass('public.contact_messages') is not null then
    for r in execute 'select to_jsonb(x) as row_data from public.contact_messages x where x.is_unread=true and x.created_at >= now() - interval ''30 days''' loop
      v := r.row_data; v_id := v->>'id';
      perform public.admin_event_emit_v18('contact:created:'||v_id,'contact.created','contact','high','Tin nhắn liên hệ mới · '||coalesce(v->>'topic','Khác'),
        coalesce(v->>'full_name','Khách hàng')||' đã gửi lời nhắn cần phản hồi.','contact_message',v_id,
        '/admin/newsletter/messages/'||v_id,'Đọc tin nhắn',null,coalesce(v->>'full_name',''),coalesce(v->>'email',''),
        jsonb_build_object('topic',v->>'topic','backfilled',true),coalesce(nullif(v->>'created_at','')::timestamptz,now()));
    end loop;
  end if;

  if to_regclass('public.newsletter_subscribers') is not null then
    for r in execute 'select to_jsonb(x) as row_data from public.newsletter_subscribers x where x.is_unread=true and x.created_at >= now() - interval ''30 days''' loop
      v := r.row_data; v_id := v->>'id';
      perform public.admin_event_emit_v18('newsletter:created:'||v_id,'newsletter.subscribed','marketing','info','Có người đăng ký newsletter',
        coalesce(nullif(v->>'full_name',''),v->>'email','Khách hàng')||' đã đồng ý nhận bản tin GUAMAISON.',
        'newsletter_subscriber',v_id,'/admin/newsletter/'||v_id,'Xem người đăng ký',null,coalesce(v->>'full_name',''),coalesce(v->>'email',''),
        jsonb_build_object('source',v->>'source','backfilled',true),coalesce(nullif(v->>'created_at','')::timestamptz,now()));
    end loop;
  end if;
end $$;

comment on table public.admin_events is 'Shared Admin action inbox. Separate from customer broadcasts and user_notifications.';

commit;

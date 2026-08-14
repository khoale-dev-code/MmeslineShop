-- GUAMAISON Shop Filters v20
-- Run once in Supabase SQL Editor before using the admin screen.

create extension if not exists pgcrypto;

create table if not exists public.shop_filter_groups (
    id uuid primary key default gen_random_uuid(),
    key text not null unique check (key ~ '^[a-z][a-z0-9_]{1,31}$'),
    label text not null check (char_length(label) between 1 and 80),
    display_type text not null default 'chips'
        check (display_type in ('chips', 'checkbox', 'color')),
    sort_order integer not null default 0 check (sort_order between 0 and 9999),
    is_active boolean not null default true,
    is_system boolean not null default false,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.shop_filter_options (
    id uuid primary key default gen_random_uuid(),
    group_id uuid not null references public.shop_filter_groups(id) on delete cascade,
    value text not null check (value ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'),
    label text not null check (char_length(label) between 1 and 80),
    color_hex text null check (color_hex is null or color_hex ~ '^#[0-9A-Fa-f]{6}$'),
    sort_order integer not null default 0 check (sort_order between 0 and 9999),
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (group_id, value)
);

create index if not exists idx_shop_filter_groups_public
    on public.shop_filter_groups (is_active, sort_order);
create index if not exists idx_shop_filter_options_public
    on public.shop_filter_options (group_id, is_active, sort_order);
create index if not exists idx_products_tags_gin
    on public.products using gin (tags);

create or replace function public.gm_shop_filter_touch_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists trg_shop_filter_groups_updated_at on public.shop_filter_groups;
create trigger trg_shop_filter_groups_updated_at
before update on public.shop_filter_groups
for each row execute function public.gm_shop_filter_touch_updated_at();

drop trigger if exists trg_shop_filter_options_updated_at on public.shop_filter_options;
create trigger trg_shop_filter_options_updated_at
before update on public.shop_filter_options
for each row execute function public.gm_shop_filter_touch_updated_at();

alter table public.shop_filter_groups enable row level security;
alter table public.shop_filter_options enable row level security;

drop policy if exists "Public reads active shop filter groups" on public.shop_filter_groups;
create policy "Public reads active shop filter groups"
on public.shop_filter_groups for select
to anon, authenticated
using (is_active = true);

drop policy if exists "Public reads active shop filter options" on public.shop_filter_options;
create policy "Public reads active shop filter options"
on public.shop_filter_options for select
to anon, authenticated
using (
    is_active = true
    and exists (
        select 1 from public.shop_filter_groups g
        where g.id = group_id and g.is_active = true
    )
);

grant select on public.shop_filter_groups to anon, authenticated;
grant select on public.shop_filter_options to anon, authenticated;

insert into public.shop_filter_groups (key, label, display_type, sort_order, is_active, is_system)
values
    ('color', 'Màu sắc', 'color', 10, true, true),
    ('chatlieu', 'Chất liệu', 'chips', 20, true, true),
    ('loai', 'Loại sản phẩm', 'checkbox', 30, true, true)
on conflict (key) do update set
    label = excluded.label,
    is_system = true;

with seed(group_key, value, label, color_hex, sort_order) as (
    values
        ('color', 'den', 'Đen', '#111827', 10),
        ('color', 'trang', 'Trắng', '#F8FAFC', 20),
        ('color', 'be', 'Be', '#D6B88D', 30),
        ('color', 'nau', 'Nâu', '#7C4A2D', 40),
        ('color', 'xanh-duong', 'Xanh dương', '#2563EB', 50),
        ('color', 'do', 'Đỏ', '#DC2626', 60),
        ('chatlieu', 'cotton', 'Cotton', null, 10),
        ('chatlieu', 'linen', 'Linen', null, 20),
        ('chatlieu', 'denim', 'Denim', null, 30),
        ('chatlieu', 'kaki', 'Kaki', null, 40),
        ('chatlieu', 'len', 'Len', null, 50),
        ('loai', 'ao', 'Áo', null, 10),
        ('loai', 'quan', 'Quần', null, 20),
        ('loai', 'vay', 'Váy', null, 30),
        ('loai', 'giay', 'Giày', null, 40),
        ('loai', 'tui-xach', 'Túi xách', null, 50)
)
insert into public.shop_filter_options (group_id, value, label, color_hex, sort_order, is_active)
select g.id, s.value, s.label, s.color_hex, s.sort_order, true
from seed s
join public.shop_filter_groups g on g.key = s.group_key
on conflict (group_id, value) do update set
    label = excluded.label,
    color_hex = excluded.color_hex;

create or replace function public.filter_storefront_product_ids(p_tokens text[] default '{}')
returns table(product_id uuid)
language sql
stable
security definer
set search_path = public
as $$
    with selected as (
        select distinct
            lower(trim(token)) as token,
            split_part(lower(trim(token)), ':', 1) as group_key
        from unnest(coalesce(p_tokens, '{}'::text[])) as token
        where trim(token) ~ '^[a-z][a-z0-9_]{1,31}:[a-z0-9]+(?:-[a-z0-9]+)*$'
    ),
    selected_groups as (
        select distinct group_key from selected
    )
    select p.id as product_id
    from public.products p
    where p.is_active = true
      and p.deleted_at is null
      and not exists (
          select 1
          from selected_groups sg
          where not exists (
              select 1
              from unnest(coalesce(p.tags, '{}'::text[])) product_tag
              join selected s
                on s.group_key = sg.group_key
               and lower(trim(product_tag)) = s.token
          )
      );
$$;

revoke all on function public.filter_storefront_product_ids(text[]) from public;
grant execute on function public.filter_storefront_product_ids(text[]) to anon, authenticated, service_role;

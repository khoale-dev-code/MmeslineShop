-- GUAMAISON Media Studio v14
-- Run after 20260809210000_contact_center_v13.sql.

alter table public.contact_page_settings
  add column if not exists hero_media_url text not null default '';

do $$
begin
  if not exists (
    select 1
      from pg_constraint
     where conname = 'contact_page_settings_hero_media_url_v14'
       and conrelid = 'public.contact_page_settings'::regclass
  ) then
    alter table public.contact_page_settings
      add constraint contact_page_settings_hero_media_url_v14
      check (
        hero_media_url = ''
        or hero_media_url like 'https://%'
        or hero_media_url like '/static/%'
      );
  end if;
end;
$$;

comment on column public.contact_page_settings.hero_media_url is
  'Optional HTTPS image shown in the Contact page hero; validated again by ContactService.';


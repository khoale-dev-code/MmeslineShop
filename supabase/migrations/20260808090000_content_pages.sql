BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS public.content_pages (
    slug text PRIMARY KEY,
    content jsonb NOT NULL DEFAULT '{}'::jsonb,
    version integer NOT NULL DEFAULT 1,
    published_at timestamptz NOT NULL DEFAULT now(),
    published_by uuid,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT content_pages_slug_valid CHECK (slug ~ '^[a-z0-9][a-z0-9_-]{0,79}$'),
    CONSTRAINT content_pages_content_object CHECK (jsonb_typeof(content) = 'object'),
    CONSTRAINT content_pages_version_valid CHECK (version >= 1)
);

CREATE TABLE IF NOT EXISTS public.content_page_drafts (
    slug text PRIMARY KEY,
    content jsonb NOT NULL DEFAULT '{}'::jsonb,
    version integer NOT NULL DEFAULT 1,
    base_published_version integer NOT NULL DEFAULT 0,
    updated_by uuid,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT content_page_drafts_slug_valid CHECK (slug ~ '^[a-z0-9][a-z0-9_-]{0,79}$'),
    CONSTRAINT content_page_drafts_content_object CHECK (jsonb_typeof(content) = 'object'),
    CONSTRAINT content_page_drafts_version_valid CHECK (version >= 1),
    CONSTRAINT content_page_drafts_base_version_valid CHECK (base_published_version >= 0)
);

CREATE TABLE IF NOT EXISTS public.content_page_revisions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    slug text NOT NULL,
    content jsonb NOT NULL,
    version integer NOT NULL,
    created_by uuid,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT content_page_revisions_content_object CHECK (jsonb_typeof(content) = 'object'),
    CONSTRAINT content_page_revisions_version_valid CHECK (version >= 1),
    CONSTRAINT content_page_revisions_unique_version UNIQUE (slug, version)
);

CREATE INDEX IF NOT EXISTS idx_content_page_revisions_slug_created
    ON public.content_page_revisions (slug, created_at DESC);

CREATE OR REPLACE FUNCTION public.touch_content_page_updated_at()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = public
AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_touch_content_pages ON public.content_pages;
CREATE TRIGGER trg_touch_content_pages
BEFORE UPDATE ON public.content_pages
FOR EACH ROW EXECUTE FUNCTION public.touch_content_page_updated_at();

DROP TRIGGER IF EXISTS trg_touch_content_page_drafts ON public.content_page_drafts;
CREATE TRIGGER trg_touch_content_page_drafts
BEFORE UPDATE ON public.content_page_drafts
FOR EACH ROW EXECUTE FUNCTION public.touch_content_page_updated_at();

CREATE OR REPLACE FUNCTION public.publish_content_page(
    p_slug text,
    p_expected_draft_version integer,
    p_user_id uuid DEFAULT NULL
)
RETURNS TABLE (
    slug text,
    content jsonb,
    version integer,
    published_at timestamptz,
    published_by uuid
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_draft public.content_page_drafts%ROWTYPE;
    v_current public.content_pages%ROWTYPE;
    v_next_version integer;
BEGIN
    SELECT d.*
      INTO v_draft
      FROM public.content_page_drafts AS d
     WHERE d.slug = p_slug
     FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'content_page_draft_not_found'
            USING ERRCODE = 'P0002';
    END IF;

    IF v_draft.version <> p_expected_draft_version THEN
        RAISE EXCEPTION 'content_page_version_conflict'
            USING ERRCODE = '40901';
    END IF;

    SELECT p.*
      INTO v_current
      FROM public.content_pages AS p
     WHERE p.slug = p_slug
     FOR UPDATE;

    IF v_current.slug IS NOT NULL
   AND v_draft.base_published_version <> v_current.version THEN
    RAISE EXCEPTION 'content_page_version_conflict'
        USING ERRCODE = '40901';
    END IF;

    IF v_current.slug IS NOT NULL THEN
        INSERT INTO public.content_page_revisions (
            slug, content, version, created_by
        ) VALUES (
            v_current.slug,
            v_current.content,
            v_current.version,
            p_user_id
        )
        ON CONFLICT (slug, version) DO NOTHING;
        v_next_version := v_current.version + 1;
    ELSE
        v_next_version := 1;
    END IF;

    INSERT INTO public.content_pages AS target (
        slug, content, version, published_at, published_by
    ) VALUES (
        p_slug,
        v_draft.content,
        v_next_version,
        now(),
        p_user_id
    )
    ON CONFLICT (slug) DO UPDATE SET
        content = EXCLUDED.content,
        version = EXCLUDED.version,
        published_at = EXCLUDED.published_at,
        published_by = EXCLUDED.published_by;

    UPDATE public.content_page_drafts AS d
       SET base_published_version = v_next_version,
           updated_by = p_user_id,
           updated_at = now()
     WHERE d.slug = p_slug;

    RETURN QUERY
    SELECT p.slug, p.content, p.version, p.published_at, p.published_by
      FROM public.content_pages AS p
     WHERE p.slug = p_slug;
END;
$$;

INSERT INTO public.content_pages (
    slug, content, version, published_at
) VALUES (
    'about',
    '{"schema_version":1}'::jsonb,
    1,
    now()
)
ON CONFLICT (slug) DO NOTHING;

INSERT INTO public.content_page_drafts (
    slug, content, version, base_published_version
) VALUES (
    'about',
    '{"schema_version":1}'::jsonb,
    1,
    1
)
ON CONFLICT (slug) DO NOTHING;

ALTER TABLE public.content_pages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.content_page_drafts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.content_page_revisions ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON public.content_pages FROM anon, authenticated;
REVOKE ALL ON public.content_page_drafts FROM anon, authenticated;
REVOKE ALL ON public.content_page_revisions FROM anon, authenticated;

GRANT SELECT ON public.content_pages TO anon, authenticated;
GRANT ALL ON public.content_pages TO service_role;
GRANT ALL ON public.content_page_drafts TO service_role;
GRANT ALL ON public.content_page_revisions TO service_role;

DROP POLICY IF EXISTS content_pages_public_read ON public.content_pages;
CREATE POLICY content_pages_public_read
ON public.content_pages
FOR SELECT
TO anon, authenticated
USING (published_at IS NOT NULL);

REVOKE ALL ON FUNCTION public.publish_content_page(text, integer, uuid)
FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.publish_content_page(text, integer, uuid)
TO service_role;

COMMIT;

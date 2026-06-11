


SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;


COMMENT ON SCHEMA "public" IS 'standard public schema';



CREATE EXTENSION IF NOT EXISTS "pg_stat_statements" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "pgcrypto" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "supabase_vault" WITH SCHEMA "vault";






CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA "extensions";






CREATE TYPE "public"."shipment_status" AS ENUM (
    'pending',
    'confirmed',
    'picking',
    'packed',
    'waiting_pickup',
    'picked',
    'in_transit',
    'out_for_delivery',
    'delivered',
    'failed',
    'returned',
    'cancelled'
);


ALTER TYPE "public"."shipment_status" OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."add_item_to_cart"("p_user_id" "uuid", "p_product_id" "uuid", "p_quantity" integer, "p_size" "text") RETURNS json
    LANGUAGE "plpgsql"
    AS $$
DECLARE
  v_item JSON;
BEGIN
  INSERT INTO cart_items (user_id, product_id, quantity, size)
  VALUES (p_user_id, p_product_id, p_quantity, p_size)
  ON CONFLICT (user_id, product_id, size) 
  DO UPDATE SET 
    quantity = cart_items.quantity + EXCLUDED.quantity,
    created_at = NOW()
  RETURNING row_to_json(cart_items.*) INTO v_item;

  RETURN v_item;
END;
$$;


ALTER FUNCTION "public"."add_item_to_cart"("p_user_id" "uuid", "p_product_id" "uuid", "p_quantity" integer, "p_size" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."apply_coupon"("p_code" "text", "p_user_id" "uuid", "p_order_id" "uuid") RETURNS "jsonb"
    LANGUAGE "plpgsql"
    AS $$

DECLARE

    v_coupon coupons%ROWTYPE;

    v_discount NUMERIC := 0;

    v_total NUMERIC := 0;

    v_applicable_total NUMERIC := 0;

    v_usage_count INT;

BEGIN

    -- LOCK coupon (fix race condition)

    SELECT * INTO v_coupon

    FROM coupons

    WHERE code = UPPER(TRIM(p_code))

    FOR UPDATE;



    IF NOT FOUND OR v_coupon.is_active = FALSE THEN

        RETURN jsonb_build_object('valid', FALSE, 'error', 'Invalid coupon');

    END IF;



    -- Time check

    IF v_coupon.starts_at IS NOT NULL AND now() < v_coupon.starts_at THEN

        RETURN jsonb_build_object('valid', FALSE, 'error', 'Not started');

    END IF;



    IF v_coupon.expires_at IS NOT NULL AND now() > v_coupon.expires_at THEN

        RETURN jsonb_build_object('valid', FALSE, 'error', 'Expired');

    END IF;



    -- Usage limit (global)

    IF v_coupon.usage_limit IS NOT NULL THEN

        SELECT COUNT(*) INTO v_usage_count

        FROM coupon_usages

        WHERE coupon_id = v_coupon.id;



        IF v_usage_count >= v_coupon.usage_limit THEN

            RETURN jsonb_build_object('valid', FALSE, 'error', 'Usage limit reached');

        END IF;

    END IF;



    -- Usage per user

    IF v_coupon.usage_per_user IS NOT NULL THEN

        SELECT COUNT(*) INTO v_usage_count

        FROM coupon_usages

        WHERE coupon_id = v_coupon.id AND user_id = p_user_id;



        IF v_usage_count >= v_coupon.usage_per_user THEN

            RETURN jsonb_build_object('valid', FALSE, 'error', 'User limit reached');

        END IF;

    END IF;



    -- SEGMENT CHECK

    IF EXISTS (

        SELECT 1 FROM coupon_segments WHERE coupon_id = v_coupon.id

    ) THEN

        IF NOT EXISTS (

            SELECT 1

            FROM coupon_segments cs

            WHERE cs.coupon_id = v_coupon.id

              AND is_user_in_segment(p_user_id, cs.segment)

        ) THEN

            RETURN jsonb_build_object('valid', FALSE, 'error', 'Not eligible');

        END IF;

    END IF;



    -- TOTAL ORDER

    SELECT SUM(price * quantity)

    INTO v_total

    FROM order_items

    WHERE order_id = p_order_id;



    -- APPLICABLE TOTAL

    SELECT SUM(oi.price * oi.quantity)

    INTO v_applicable_total

    FROM order_items oi

    WHERE oi.order_id = p_order_id

    AND (

        NOT EXISTS (SELECT 1 FROM coupon_products WHERE coupon_id = v_coupon.id)

        OR oi.product_id IN (

            SELECT product_id FROM coupon_products WHERE coupon_id = v_coupon.id

        )

    )

    AND (

        NOT EXISTS (SELECT 1 FROM coupon_categories WHERE coupon_id = v_coupon.id)

        OR oi.category_id IN (

            SELECT category_id FROM coupon_categories WHERE coupon_id = v_coupon.id

        )

    );



    IF v_applicable_total IS NULL THEN

        RETURN jsonb_build_object('valid', FALSE, 'error', 'No applicable products');

    END IF;



    -- MIN ORDER

    IF v_applicable_total < v_coupon.min_order_value THEN

        RETURN jsonb_build_object('valid', FALSE, 'error', 'Minimum not met');

    END IF;



    -- CALCULATE

    IF v_coupon.discount_type = 'percent' THEN

        v_discount := v_applicable_total * v_coupon.discount_value / 100;

        IF v_coupon.max_discount IS NOT NULL THEN

            v_discount := LEAST(v_discount, v_coupon.max_discount);

        END IF;



    ELSIF v_coupon.discount_type = 'fixed' THEN

        v_discount := v_coupon.discount_value;



    ELSIF v_coupon.discount_type = 'free_shipping' THEN

        v_discount := 0; -- xử lý phía order shipping

    END IF;



    v_discount := LEAST(v_discount, v_applicable_total);



    RETURN jsonb_build_object(

        'valid', TRUE,

        'discount', v_discount,

        'final_total', v_total - v_discount

    );

END;

$$;


ALTER FUNCTION "public"."apply_coupon"("p_code" "text", "p_user_id" "uuid", "p_order_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."fan_out_notification"("p_notification_id" "uuid") RETURNS integer
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE
  v_count integer := 0;
BEGIN
  INSERT INTO user_notifications (user_id, notification_id, is_read, is_deleted)
  SELECT id, p_notification_id, false, false
  FROM users
  WHERE role = 'customer'
  ON CONFLICT (user_id, notification_id) DO NOTHING;

  GET DIAGNOSTICS v_count = ROW_COUNT;
  RETURN v_count;
END;
$$;


ALTER FUNCTION "public"."fan_out_notification"("p_notification_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_cart_total_quantity"("p_user_id" "uuid") RETURNS integer
    LANGUAGE "plpgsql"
    AS $$
BEGIN
  RETURN (
    SELECT COALESCE(SUM(quantity), 0) 
    FROM cart_items 
    WHERE user_id = p_user_id
  );
END;
$$;


ALTER FUNCTION "public"."get_cart_total_quantity"("p_user_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_product_count_by_category"() RETURNS TABLE("name" "text", "count" bigint)
    LANGUAGE "plpgsql"
    AS $$
BEGIN
  RETURN QUERY
  SELECT c.name, COUNT(p.id)
  FROM categories c
  LEFT JOIN products p ON c.id = p.category_id
  WHERE p.is_active = true
  GROUP BY c.name;
END;
$$;


ALTER FUNCTION "public"."get_product_count_by_category"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_unread_notification_count"("p_user_id" "uuid") RETURNS integer
    LANGUAGE "sql" STABLE SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
  select count(*)::integer
  from public.user_notifications un
  join public.notifications n on n.id = un.notification_id
  where un.user_id = p_user_id
    and coalesce(un.is_read, false) = false
    and coalesce(un.is_deleted, false) = false
    and coalesce(n.is_active, true) = true
    and (
      coalesce(n.is_permanent, false) = true
      or (
        (n.start_at is null or n.start_at <= now())
        and (n.end_at is null or n.end_at >= now())
      )
    );
$$;


ALTER FUNCTION "public"."get_unread_notification_count"("p_user_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."is_user_in_segment"("p_user_id" "uuid", "p_segment" "text") RETURNS boolean
    LANGUAGE "plpgsql"
    AS $$

BEGIN

    IF p_segment = 'new_user' THEN

        RETURN NOT EXISTS (

            SELECT 1 FROM orders WHERE user_id = p_user_id

        );

    ELSIF p_segment = 'vip' THEN

        RETURN EXISTS (

            SELECT 1 FROM users 

            WHERE id = p_user_id AND is_vip = TRUE

        );

    END IF;



    RETURN FALSE;

END;

$$;


ALTER FUNCTION "public"."is_user_in_segment"("p_user_id" "uuid", "p_segment" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."log_product_event"("p_product_id" "uuid", "p_channel" "text", "p_source" "text", "p_event_type" "text", "p_revenue" numeric DEFAULT 0, "p_qty" integer DEFAULT 1) RETURNS "void"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    INSERT INTO product_analytics (
        product_id, channel, source, report_date, 
        views, add_to_carts, sold, wishlist_count, revenue
    )
    VALUES (
        p_product_id, 
        COALESCE(p_channel, 'web'), 
        COALESCE(p_source, 'organic'), 
        CURRENT_DATE,
        CASE WHEN p_event_type = 'view' THEN p_qty ELSE 0 END,
        CASE WHEN p_event_type = 'cart' THEN p_qty ELSE 0 END,
        CASE WHEN p_event_type = 'sold' THEN p_qty ELSE 0 END,
        CASE WHEN p_event_type = 'wishlist' THEN p_qty ELSE 0 END,
        p_revenue
    )
    ON CONFLICT (product_id, channel, source, report_date) 
    DO UPDATE SET
        views = product_analytics.views + EXCLUDED.views,
        add_to_carts = product_analytics.add_to_carts + EXCLUDED.add_to_carts,
        sold = product_analytics.sold + EXCLUDED.sold,
        wishlist_count = product_analytics.wishlist_count + EXCLUDED.wishlist_count,
        revenue = product_analytics.revenue + EXCLUDED.revenue;
END;
$$;


ALTER FUNCTION "public"."log_product_event"("p_product_id" "uuid", "p_channel" "text", "p_source" "text", "p_event_type" "text", "p_revenue" numeric, "p_qty" integer) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."rls_auto_enable"() RETURNS "event_trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'pg_catalog'
    AS $$
DECLARE
  cmd record;
BEGIN
  FOR cmd IN
    SELECT *
    FROM pg_event_trigger_ddl_commands()
    WHERE command_tag IN ('CREATE TABLE', 'CREATE TABLE AS', 'SELECT INTO')
      AND object_type IN ('table','partitioned table')
  LOOP
     IF cmd.schema_name IS NOT NULL AND cmd.schema_name IN ('public') AND cmd.schema_name NOT IN ('pg_catalog','information_schema') AND cmd.schema_name NOT LIKE 'pg_toast%' AND cmd.schema_name NOT LIKE 'pg_temp%' THEN
      BEGIN
        EXECUTE format('alter table if exists %s enable row level security', cmd.object_identity);
        RAISE LOG 'rls_auto_enable: enabled RLS on %', cmd.object_identity;
      EXCEPTION
        WHEN OTHERS THEN
          RAISE LOG 'rls_auto_enable: failed to enable RLS on %', cmd.object_identity;
      END;
     ELSE
        RAISE LOG 'rls_auto_enable: skip % (either system schema or not in enforced list: %.)', cmd.object_identity, cmd.schema_name;
     END IF;
  END LOOP;
END;
$$;


ALTER FUNCTION "public"."rls_auto_enable"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."sync_product_stock"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    -- Tính tổng stock từ tất cả variants của product bị ảnh hưởng
    UPDATE public.products
    SET stock = (
        SELECT COALESCE(SUM(pv.stock), 0)
        FROM public.product_variants pv
        WHERE pv.product_id = COALESCE(NEW.product_id, OLD.product_id)
    )
    WHERE id = COALESCE(NEW.product_id, OLD.product_id);
 
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."sync_product_stock"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_modified_column"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."update_modified_column"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_updated_at_column"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."update_updated_at_column"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_user_points_balance"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    UPDATE users 
    SET points = (SELECT COALESCE(SUM(amount), 0) FROM loyalty_transactions WHERE user_id = NEW.user_id)
    WHERE id = NEW.user_id;
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."update_user_points_balance"() OWNER TO "postgres";

SET default_tablespace = '';

SET default_table_access_method = "heap";


CREATE TABLE IF NOT EXISTS "public"."admin_roles" (
    "slug" "text" NOT NULL,
    "name" "text" NOT NULL,
    "permissions" "jsonb" DEFAULT '[]'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."admin_roles" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."audit_logs" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "user_id" "uuid",
    "action" character varying NOT NULL,
    "table_name" character varying NOT NULL,
    "record_id" character varying,
    "old_values" "jsonb",
    "new_values" "jsonb",
    "ip_address" character varying,
    "created_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."audit_logs" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."brands" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "name" character varying(100) NOT NULL,
    "slug" character varying(100) NOT NULL,
    "logo_url" "text",
    "created_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."brands" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."carrier_status_mapping" (
    "id" integer NOT NULL,
    "provider" character varying(50) NOT NULL,
    "carrier_status" character varying(100) NOT NULL,
    "internal_status" "public"."shipment_status" NOT NULL
);


ALTER TABLE "public"."carrier_status_mapping" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."carrier_status_mapping_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."carrier_status_mapping_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."carrier_status_mapping_id_seq" OWNED BY "public"."carrier_status_mapping"."id";



CREATE TABLE IF NOT EXISTS "public"."cart_items" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "user_id" "uuid",
    "product_id" "uuid",
    "quantity" integer DEFAULT 1 NOT NULL,
    "size" "text",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "color" "text",
    "variant_id" "uuid"
);


ALTER TABLE "public"."cart_items" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."categories" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "name" "text" NOT NULL,
    "slug" "text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "image_url" "text",
    "video_url" "text",
    "description" "text",
    "is_active" boolean DEFAULT true NOT NULL,
    "sort_order" integer DEFAULT 0 NOT NULL,
    "meta_title" "text",
    "meta_description" "text",
    "show_on_home" boolean DEFAULT false NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "parent_id" "uuid"
);


ALTER TABLE "public"."categories" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."collection_products" (
    "collection_id" "uuid" NOT NULL,
    "product_id" "uuid" NOT NULL,
    "assigned_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."collection_products" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."collections" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "name" "text" NOT NULL,
    "slug" "text" NOT NULL,
    "description" "text",
    "image_url" "text",
    "video_url" "text",
    "is_active" boolean DEFAULT true NOT NULL,
    "show_on_home" boolean DEFAULT false NOT NULL,
    "sort_order" integer DEFAULT 0 NOT NULL,
    "meta_title" "text",
    "meta_description" "text",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."collections" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."coupon_categories" (
    "coupon_id" "uuid" NOT NULL,
    "category_id" "uuid" NOT NULL
);


ALTER TABLE "public"."coupon_categories" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."coupon_products" (
    "coupon_id" "uuid" NOT NULL,
    "product_id" "uuid" NOT NULL
);


ALTER TABLE "public"."coupon_products" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."coupon_usages" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "coupon_id" "uuid" NOT NULL,
    "order_id" "uuid" NOT NULL,
    "user_id" "uuid" NOT NULL,
    "discount_amount" numeric(12,2),
    "used_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."coupon_usages" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."coupons" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "code" character varying(50) NOT NULL,
    "description" "text",
    "discount_type" character varying(20) NOT NULL,
    "discount_value" numeric(12,2) DEFAULT 0,
    "max_discount" numeric(12,2),
    "min_order_value" numeric(12,2) DEFAULT 0,
    "is_stackable" boolean DEFAULT false,
    "usage_limit" integer,
    "usage_per_user" integer,
    "starts_at" timestamp with time zone,
    "expires_at" timestamp with time zone,
    "is_active" boolean DEFAULT true,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "is_first_order_only" boolean DEFAULT false,
    "max_usage_per_day" integer,
    "image_url" "text",
    "applicable_channel" character varying DEFAULT 'all'::character varying,
    "min_loyalty_points" integer DEFAULT 0,
    CONSTRAINT "coupons_discount_type_check" CHECK ((("discount_type")::"text" = ANY ((ARRAY['percent'::character varying, 'fixed'::character varying, 'free_shipping'::character varying])::"text"[])))
);


ALTER TABLE "public"."coupons" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."customers" (
    "id" "uuid" NOT NULL,
    "name" "text"
);


ALTER TABLE "public"."customers" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."favorites" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "user_id" "uuid" NOT NULL,
    "product_id" "uuid" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "channel" "text" DEFAULT 'web'::"text",
    "source" "text" DEFAULT 'organic'::"text"
);


ALTER TABLE "public"."favorites" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."flash_sale_items" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "flash_sale_id" "uuid",
    "product_id" "uuid",
    "variant_id" "uuid",
    "promotional_price" numeric(15,2) NOT NULL,
    "quantity_limit" integer NOT NULL,
    "sold_quantity" integer DEFAULT 0
);


ALTER TABLE "public"."flash_sale_items" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."flash_sales" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "name" character varying(255) NOT NULL,
    "starts_at" timestamp with time zone NOT NULL,
    "ends_at" timestamp with time zone NOT NULL,
    "is_active" boolean DEFAULT true,
    "created_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."flash_sales" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."inventory_logs" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "product_id" "uuid",
    "variant_id" "uuid",
    "change_type" character varying(50) NOT NULL,
    "quantity_changed" integer NOT NULL,
    "stock_after" integer NOT NULL,
    "reference_id" "uuid",
    "note" "text",
    "created_by" "uuid",
    "created_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."inventory_logs" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."loyalty_transactions" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "user_id" "uuid",
    "amount" integer NOT NULL,
    "transaction_type" character varying NOT NULL,
    "description" "text",
    "reference_id" character varying,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "expires_at" timestamp with time zone
);


ALTER TABLE "public"."loyalty_transactions" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."notifications" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "title" character varying(255) NOT NULL,
    "content" "text" NOT NULL,
    "is_active" boolean DEFAULT true,
    "is_permanent" boolean DEFAULT false,
    "start_at" timestamp with time zone,
    "end_at" timestamp with time zone,
    "link" character varying(500),
    "link_text" character varying(100),
    "sort_order" integer DEFAULT 0,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."notifications" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."order_items" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "order_id" "uuid",
    "product_id" "uuid",
    "quantity" integer NOT NULL,
    "unit_price" numeric(12,0) NOT NULL,
    "variant_id" "uuid",
    "product_name" character varying(255) DEFAULT ''::character varying NOT NULL,
    "variant_label" character varying(255)
);


ALTER TABLE "public"."order_items" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."orders" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "user_id" "uuid",
    "total_amount" numeric(14,0) DEFAULT 0 NOT NULL,
    "shipping_address" "jsonb",
    "status" "text" DEFAULT 'pending'::"text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "payment_method" "text" DEFAULT 'COD'::"text",
    "payment_status" "text" DEFAULT 'pending'::"text",
    "order_notes" "text",
    "coupon_id" "uuid",
    "discount_amount" numeric(12,2) DEFAULT 0,
    "shipping_fee" numeric(12,2) DEFAULT 0,
    "sales_channel" "text" DEFAULT 'web'::"text",
    "code" "text",
    "customer_name" "text",
    "customer_phone" "text",
    "customer_id" "uuid",
    "cashier_id" "uuid",
    "cashier_name" "text",
    "staff_id" "uuid",
    "staff_name" "text",
    "subtotal_amount" numeric DEFAULT 0,
    "cash_received" numeric DEFAULT 0,
    "change_amount" numeric DEFAULT 0,
    "vat_enabled" boolean DEFAULT false,
    "vat_rate" numeric DEFAULT 0,
    "vat_amount" numeric DEFAULT 0,
    "delivery_later" boolean DEFAULT false,
    "delivery_info" "jsonb" DEFAULT '{}'::"jsonb",
    "pricebook_id" "text",
    CONSTRAINT "orders_status_check" CHECK (("status" = ANY (ARRAY['pending'::"text", 'confirmed'::"text", 'packed'::"text", 'shipped'::"text", 'shipping'::"text", 'delivered'::"text", 'completed'::"text", 'cancelled'::"text", 'failed'::"text", 'returned'::"text"])))
);


ALTER TABLE "public"."orders" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."payments" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "order_id" "uuid",
    "provider" character varying(50) NOT NULL,
    "transaction_id" character varying(255),
    "amount" numeric(15,2) NOT NULL,
    "status" character varying(50) DEFAULT 'pending'::character varying NOT NULL,
    "raw_response" "jsonb",
    "paid_at" timestamp with time zone,
    "created_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."payments" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."product_analytics" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "product_id" "uuid",
    "channel" "text" NOT NULL,
    "source" "text" DEFAULT 'organic'::"text",
    "views" integer DEFAULT 0,
    "add_to_carts" integer DEFAULT 0,
    "sold" integer DEFAULT 0,
    "wishlist_count" integer DEFAULT 0,
    "revenue" numeric DEFAULT 0,
    "report_date" "date" DEFAULT CURRENT_DATE,
    "created_at" timestamp with time zone DEFAULT "now"(),
    CONSTRAINT "chk_channel" CHECK (("channel" = ANY (ARRAY['web'::"text", 'pos'::"text", 'tiktok'::"text", 'shopee'::"text", 'facebook'::"text", 'instagram'::"text"])))
);


ALTER TABLE "public"."product_analytics" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."product_categories" (
    "product_id" "uuid" NOT NULL,
    "category_id" "uuid" NOT NULL,
    "assigned_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."product_categories" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."product_images" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "product_id" "uuid" NOT NULL,
    "url" "text" NOT NULL,
    "is_primary" boolean DEFAULT false,
    "sort_order" integer DEFAULT 0 NOT NULL
);


ALTER TABLE "public"."product_images" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."product_reviews" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "product_id" "uuid",
    "user_id" "uuid",
    "order_id" "uuid",
    "rating" integer,
    "comment" "text",
    "images" "text"[] DEFAULT '{}'::"text"[],
    "reply_comment" "text",
    "is_hidden" boolean DEFAULT false,
    "created_at" timestamp with time zone DEFAULT "now"(),
    CONSTRAINT "product_reviews_rating_check" CHECK ((("rating" >= 1) AND ("rating" <= 5)))
);


ALTER TABLE "public"."product_reviews" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."product_variants" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "product_id" "uuid" NOT NULL,
    "size" "text" NOT NULL,
    "color_name" "text" NOT NULL,
    "color_hex" "text",
    "sku" "text",
    "price_override" numeric,
    "stock" integer DEFAULT 0 NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "barcode" "text",
    "cost_price" numeric(12,0),
    "compare_at_price" numeric(12,0),
    "sort_order" integer DEFAULT 0
);


ALTER TABLE "public"."product_variants" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."products" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "name" "text" NOT NULL,
    "description" "text",
    "price" numeric(12,0) DEFAULT 0 NOT NULL,
    "stock" integer DEFAULT 0 NOT NULL,
    "thumbnail_url" "text",
    "is_featured" boolean DEFAULT false,
    "is_active" boolean DEFAULT true,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "rating" numeric DEFAULT 4.5,
    "sold_count" integer DEFAULT 0,
    "discount" integer DEFAULT 0,
    "slug" "text" NOT NULL,
    "meta_title" "text",
    "meta_description" "text",
    "gender" "text",
    "tags" "text"[],
    "deleted_at" timestamp with time zone,
    "created_by" "uuid",
    "textsearchable_index_col" "tsvector" GENERATED ALWAYS AS ("to_tsvector"('"simple"'::"regconfig", ((COALESCE("name", ''::"text") || ' '::"text") || COALESCE("description", ''::"text")))) STORED,
    "brand_id" "uuid",
    "attributes" "jsonb" DEFAULT '{}'::"jsonb",
    "barcode" "text",
    "compare_at_price" numeric(12,0),
    "cost_price" numeric(12,0),
    "sku" "text",
    "seo_title" "text",
    "seo_description" "text",
    "seo_keywords" "text",
    "seo_image_url" "text",
    "search_keywords" "text",
    "product_status" "text" DEFAULT 'active'::"text",
    "allow_backorder" boolean DEFAULT false,
    "low_stock_threshold" integer DEFAULT 5,
    "description_html" "text",
    "brand" "text" DEFAULT 'MMESTLINE'::"text",
    "meta_keywords" "text"
);


ALTER TABLE "public"."products" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."return_requests" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "order_id" "uuid" NOT NULL,
    "user_id" "uuid" NOT NULL,
    "reason" "text" NOT NULL,
    "image_url" "text" NOT NULL,
    "requested_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "status" "text" DEFAULT 'pending'::"text" NOT NULL,
    "reviewed_by" "uuid",
    "reviewed_at" timestamp with time zone,
    "admin_note" "text",
    "refunded_at" timestamp with time zone,
    "refund_amount" numeric(12,2),
    CONSTRAINT "return_requests_status_check" CHECK (("status" = ANY (ARRAY['pending'::"text", 'approved'::"text", 'rejected'::"text", 'refunded'::"text"])))
);


ALTER TABLE "public"."return_requests" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."shipment_events" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "shipment_id" "uuid",
    "status" "public"."shipment_status" NOT NULL,
    "description" "text",
    "location" character varying(255),
    "raw_data" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."shipment_events" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."shipments" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "order_id" "uuid",
    "provider" character varying(50) DEFAULT 'mock'::character varying NOT NULL,
    "tracking_code" character varying(100),
    "shipping_fee" numeric(12,2) DEFAULT 0,
    "actual_shipping_fee" numeric(12,2) DEFAULT 0,
    "cod_amount" numeric(12,2) DEFAULT 0,
    "package_index" integer DEFAULT 1,
    "weight_g" integer DEFAULT 0,
    "dimensions_json" "jsonb" DEFAULT '{"h": 0, "l": 0, "w": 0}'::"jsonb",
    "recipient_name" character varying(255) NOT NULL,
    "recipient_phone" character varying(50) NOT NULL,
    "recipient_address" "text" NOT NULL,
    "recipient_ward_code" character varying(20),
    "recipient_district_id" integer,
    "recipient_province_id" integer,
    "status" "public"."shipment_status" DEFAULT 'pending'::"public"."shipment_status",
    "delayed" boolean DEFAULT false,
    "expected_delivery_at" timestamp with time zone,
    "shipped_at" timestamp with time zone,
    "delivered_at" timestamp with time zone,
    "raw_response" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "delivery_attempts" integer DEFAULT 0,
    "failed_reason" "text"
);


ALTER TABLE "public"."shipments" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."shipping_configs" (
    "id" integer DEFAULT 1 NOT NULL,
    "freeship_threshold" numeric(12,2) DEFAULT 1500000,
    "hcm_fee" numeric(12,2) DEFAULT 25000,
    "hn_fee" numeric(12,2) DEFAULT 35000,
    "default_fee" numeric(12,2) DEFAULT 45000,
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."shipping_configs" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."shipping_providers" (
    "id" "text" NOT NULL,
    "name" "text" NOT NULL,
    "description" "text",
    "is_active" boolean DEFAULT false,
    "config" "jsonb" DEFAULT '{}'::"jsonb",
    "icon" "text",
    "sort_order" integer DEFAULT 0,
    "created_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."shipping_providers" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."store_settings" (
    "setting_key" "text" NOT NULL,
    "setting_value" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "description" "text",
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."store_settings" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."user_addresses" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "user_id" "uuid" NOT NULL,
    "full_name" "text" NOT NULL,
    "phone" "text" NOT NULL,
    "address_line" "text" NOT NULL,
    "is_default" boolean DEFAULT false,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "province" "text",
    "district" "text",
    "ward" "text",
    "note" "text"
);


ALTER TABLE "public"."user_addresses" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."user_notifications" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "uuid" NOT NULL,
    "notification_id" "uuid" NOT NULL,
    "is_read" boolean DEFAULT false,
    "is_deleted" boolean DEFAULT false,
    "read_at" timestamp with time zone,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."user_notifications" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."users" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "email" "text" NOT NULL,
    "password_hash" "text" NOT NULL,
    "full_name" "text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "phone" "text",
    "is_vip" boolean DEFAULT false,
    "role" "text" DEFAULT 'customer'::"text",
    "is_suspended" boolean DEFAULT false,
    "admin_role_slug" "text",
    "points" integer DEFAULT 0,
    "total_spent" numeric DEFAULT 0,
    "member_tier" character varying DEFAULT 'MEMBER'::character varying
);


ALTER TABLE "public"."users" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."webhook_logs" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "provider" character varying(50) NOT NULL,
    "event_type" character varying(100),
    "payload" "jsonb" NOT NULL,
    "status_code" integer,
    "error_message" "text",
    "created_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."webhook_logs" OWNER TO "postgres";


ALTER TABLE ONLY "public"."carrier_status_mapping" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."carrier_status_mapping_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."admin_roles"
    ADD CONSTRAINT "admin_roles_pkey" PRIMARY KEY ("slug");



ALTER TABLE ONLY "public"."audit_logs"
    ADD CONSTRAINT "audit_logs_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."brands"
    ADD CONSTRAINT "brands_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."brands"
    ADD CONSTRAINT "brands_slug_key" UNIQUE ("slug");



ALTER TABLE ONLY "public"."carrier_status_mapping"
    ADD CONSTRAINT "carrier_status_mapping_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."carrier_status_mapping"
    ADD CONSTRAINT "carrier_status_mapping_provider_carrier_status_key" UNIQUE ("provider", "carrier_status");



ALTER TABLE ONLY "public"."cart_items"
    ADD CONSTRAINT "cart_items_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."categories"
    ADD CONSTRAINT "categories_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."categories"
    ADD CONSTRAINT "categories_slug_key" UNIQUE ("slug");



ALTER TABLE ONLY "public"."collection_products"
    ADD CONSTRAINT "collection_products_pkey" PRIMARY KEY ("collection_id", "product_id");



ALTER TABLE ONLY "public"."collections"
    ADD CONSTRAINT "collections_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."collections"
    ADD CONSTRAINT "collections_slug_key" UNIQUE ("slug");



ALTER TABLE ONLY "public"."coupon_categories"
    ADD CONSTRAINT "coupon_categories_pkey" PRIMARY KEY ("coupon_id", "category_id");



ALTER TABLE ONLY "public"."coupon_products"
    ADD CONSTRAINT "coupon_products_pkey" PRIMARY KEY ("coupon_id", "product_id");



ALTER TABLE ONLY "public"."coupon_usages"
    ADD CONSTRAINT "coupon_usages_coupon_id_order_id_key" UNIQUE ("coupon_id", "order_id");



ALTER TABLE ONLY "public"."coupon_usages"
    ADD CONSTRAINT "coupon_usages_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."coupons"
    ADD CONSTRAINT "coupons_code_key" UNIQUE ("code");



ALTER TABLE ONLY "public"."coupons"
    ADD CONSTRAINT "coupons_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."customers"
    ADD CONSTRAINT "customers_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."favorites"
    ADD CONSTRAINT "favorites_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."flash_sale_items"
    ADD CONSTRAINT "flash_sale_items_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."flash_sales"
    ADD CONSTRAINT "flash_sales_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."inventory_logs"
    ADD CONSTRAINT "inventory_logs_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."loyalty_transactions"
    ADD CONSTRAINT "loyalty_transactions_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."notifications"
    ADD CONSTRAINT "notifications_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."order_items"
    ADD CONSTRAINT "order_items_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."orders"
    ADD CONSTRAINT "orders_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."payments"
    ADD CONSTRAINT "payments_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."product_analytics"
    ADD CONSTRAINT "product_analytics_master_key" UNIQUE ("product_id", "channel", "source", "report_date");



ALTER TABLE ONLY "public"."product_analytics"
    ADD CONSTRAINT "product_analytics_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."product_categories"
    ADD CONSTRAINT "product_categories_pkey" PRIMARY KEY ("product_id", "category_id");



ALTER TABLE ONLY "public"."product_images"
    ADD CONSTRAINT "product_images_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."product_reviews"
    ADD CONSTRAINT "product_reviews_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."product_variants"
    ADD CONSTRAINT "product_variants_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."product_variants"
    ADD CONSTRAINT "product_variants_sku_key" UNIQUE ("sku");



ALTER TABLE ONLY "public"."products"
    ADD CONSTRAINT "products_barcode_key" UNIQUE ("barcode");



ALTER TABLE ONLY "public"."products"
    ADD CONSTRAINT "products_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."return_requests"
    ADD CONSTRAINT "return_requests_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."shipment_events"
    ADD CONSTRAINT "shipment_events_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."shipments"
    ADD CONSTRAINT "shipments_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."shipping_configs"
    ADD CONSTRAINT "shipping_configs_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."shipping_providers"
    ADD CONSTRAINT "shipping_providers_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."store_settings"
    ADD CONSTRAINT "store_settings_pkey" PRIMARY KEY ("setting_key");



ALTER TABLE ONLY "public"."cart_items"
    ADD CONSTRAINT "unique_cart_item" UNIQUE ("user_id", "product_id", "size");



ALTER TABLE ONLY "public"."favorites"
    ADD CONSTRAINT "unique_user_product" UNIQUE ("user_id", "product_id");



ALTER TABLE ONLY "public"."user_notifications"
    ADD CONSTRAINT "uq_user_notif" UNIQUE ("user_id", "notification_id");



ALTER TABLE ONLY "public"."user_notifications"
    ADD CONSTRAINT "uq_user_notification" UNIQUE ("user_id", "notification_id");



ALTER TABLE ONLY "public"."user_notifications"
    ADD CONSTRAINT "uq_user_notifications_user_notif" UNIQUE ("user_id", "notification_id");



ALTER TABLE ONLY "public"."user_addresses"
    ADD CONSTRAINT "user_addresses_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."user_notifications"
    ADD CONSTRAINT "user_notifications_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."user_notifications"
    ADD CONSTRAINT "user_notifications_user_id_notification_id_key" UNIQUE ("user_id", "notification_id");



ALTER TABLE ONLY "public"."user_notifications"
    ADD CONSTRAINT "user_notifications_user_notification_unique" UNIQUE ("user_id", "notification_id");



ALTER TABLE ONLY "public"."users"
    ADD CONSTRAINT "users_email_key" UNIQUE ("email");



ALTER TABLE ONLY "public"."users"
    ADD CONSTRAINT "users_phone_unique" UNIQUE ("phone");



ALTER TABLE ONLY "public"."users"
    ADD CONSTRAINT "users_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."product_variants"
    ADD CONSTRAINT "variant_unique_combination" UNIQUE ("product_id", "size", "color_name");



CREATE INDEX "idx_cart_items_user_id" ON "public"."cart_items" USING "btree" ("user_id");



CREATE INDEX "idx_cart_user" ON "public"."cart_items" USING "btree" ("user_id");



CREATE INDEX "idx_categories_slug" ON "public"."categories" USING "btree" ("slug");



CREATE INDEX "idx_collection_products_coll" ON "public"."collection_products" USING "btree" ("collection_id");



CREATE INDEX "idx_collection_products_collection" ON "public"."collection_products" USING "btree" ("collection_id");



CREATE INDEX "idx_collection_products_prod" ON "public"."collection_products" USING "btree" ("product_id");



CREATE INDEX "idx_collection_products_product" ON "public"."collection_products" USING "btree" ("product_id");



CREATE INDEX "idx_collections_slug" ON "public"."collections" USING "btree" ("slug");



CREATE INDEX "idx_coupon_categories" ON "public"."coupon_categories" USING "btree" ("category_id");



CREATE INDEX "idx_coupon_products" ON "public"."coupon_products" USING "btree" ("product_id");



CREATE INDEX "idx_coupon_usages_user" ON "public"."coupon_usages" USING "btree" ("coupon_id", "user_id");



CREATE INDEX "idx_coupons_active" ON "public"."coupons" USING "btree" ("is_active", "starts_at", "expires_at");



CREATE INDEX "idx_favorites_product" ON "public"."favorites" USING "btree" ("product_id");



CREATE INDEX "idx_favorites_user" ON "public"."favorites" USING "btree" ("user_id");



CREATE INDEX "idx_favorites_user_id" ON "public"."favorites" USING "btree" ("user_id");



CREATE INDEX "idx_notifications_active" ON "public"."notifications" USING "btree" ("is_active") WHERE ("is_active" = true);



CREATE INDEX "idx_notifications_active_dates" ON "public"."notifications" USING "btree" ("is_active", "start_at", "end_at");



CREATE INDEX "idx_notifications_sort" ON "public"."notifications" USING "btree" ("sort_order");



CREATE INDEX "idx_order_items_order" ON "public"."order_items" USING "btree" ("order_id");



CREATE INDEX "idx_order_items_order_id" ON "public"."order_items" USING "btree" ("order_id");



CREATE INDEX "idx_orders_created_at" ON "public"."orders" USING "btree" ("created_at" DESC);



CREATE INDEX "idx_orders_shipping_address" ON "public"."orders" USING "gin" ("shipping_address");



CREATE INDEX "idx_orders_status" ON "public"."orders" USING "btree" ("status");



CREATE INDEX "idx_orders_user" ON "public"."orders" USING "btree" ("user_id");



CREATE INDEX "idx_orders_user_id" ON "public"."orders" USING "btree" ("user_id");



CREATE INDEX "idx_pa_channel" ON "public"."product_analytics" USING "btree" ("channel");



CREATE INDEX "idx_pa_date" ON "public"."product_analytics" USING "btree" ("report_date");



CREATE INDEX "idx_pa_product" ON "public"."product_analytics" USING "btree" ("product_id");



CREATE INDEX "idx_product_categories_cat" ON "public"."product_categories" USING "btree" ("category_id");



CREATE INDEX "idx_product_categories_prod" ON "public"."product_categories" USING "btree" ("product_id");



CREATE INDEX "idx_product_images_product" ON "public"."product_images" USING "btree" ("product_id");



CREATE INDEX "idx_product_variants_barcode" ON "public"."product_variants" USING "btree" ("barcode");



CREATE INDEX "idx_product_variants_sku" ON "public"."product_variants" USING "btree" ("sku");



CREATE INDEX "idx_products_barcode" ON "public"."products" USING "btree" ("barcode");



CREATE INDEX "idx_products_featured" ON "public"."products" USING "btree" ("is_featured") WHERE ("is_featured" = true);



CREATE INDEX "idx_products_is_active" ON "public"."products" USING "btree" ("is_active") WHERE ("is_active" = true);



CREATE INDEX "idx_products_sku" ON "public"."products" USING "btree" ("sku");



CREATE UNIQUE INDEX "idx_products_slug" ON "public"."products" USING "btree" ("slug");



CREATE INDEX "idx_return_requests_order" ON "public"."return_requests" USING "btree" ("order_id");



CREATE INDEX "idx_return_requests_status" ON "public"."return_requests" USING "btree" ("status");



CREATE INDEX "idx_return_requests_user" ON "public"."return_requests" USING "btree" ("user_id");



CREATE INDEX "idx_shipments_raw_response" ON "public"."shipments" USING "gin" ("raw_response");



CREATE INDEX "idx_shipments_status_created" ON "public"."shipments" USING "btree" ("status", "created_at" DESC);



CREATE INDEX "idx_shipments_tracking_code" ON "public"."shipments" USING "btree" ("tracking_code");



CREATE INDEX "idx_user_addresses_user_id" ON "public"."user_addresses" USING "btree" ("user_id");



CREATE INDEX "idx_user_notif_notif" ON "public"."user_notifications" USING "btree" ("notification_id");



CREATE INDEX "idx_user_notif_read" ON "public"."user_notifications" USING "btree" ("user_id", "is_read");



CREATE INDEX "idx_user_notif_unread" ON "public"."user_notifications" USING "btree" ("user_id", "is_read", "is_deleted") WHERE (("is_read" = false) AND ("is_deleted" = false));



CREATE INDEX "idx_user_notif_user" ON "public"."user_notifications" USING "btree" ("user_id");



CREATE INDEX "idx_variants_product" ON "public"."product_variants" USING "btree" ("product_id");



CREATE INDEX "idx_webhook_logs_provider_created" ON "public"."webhook_logs" USING "btree" ("provider", "created_at" DESC);



CREATE UNIQUE INDEX "product_variants_barcode_unique_idx" ON "public"."product_variants" USING "btree" ("barcode") WHERE (("barcode" IS NOT NULL) AND ("barcode" <> ''::"text"));



CREATE UNIQUE INDEX "product_variants_sku_unique_idx" ON "public"."product_variants" USING "btree" ("sku") WHERE (("sku" IS NOT NULL) AND ("sku" <> ''::"text"));



CREATE UNIQUE INDEX "products_barcode_unique_idx" ON "public"."products" USING "btree" ("barcode") WHERE (("barcode" IS NOT NULL) AND ("barcode" <> ''::"text"));



CREATE UNIQUE INDEX "products_sku_unique_idx" ON "public"."products" USING "btree" ("sku") WHERE (("sku" IS NOT NULL) AND ("sku" <> ''::"text"));



CREATE INDEX "textsearch_idx" ON "public"."products" USING "gin" ("textsearchable_index_col");



CREATE OR REPLACE TRIGGER "trg_sync_product_stock" AFTER INSERT OR DELETE OR UPDATE OF "stock" ON "public"."product_variants" FOR EACH ROW EXECUTE FUNCTION "public"."sync_product_stock"();



CREATE OR REPLACE TRIGGER "trigger_update_points" AFTER INSERT OR DELETE OR UPDATE ON "public"."loyalty_transactions" FOR EACH ROW EXECUTE FUNCTION "public"."update_user_points_balance"();



CREATE OR REPLACE TRIGGER "update_categories_modtime" BEFORE UPDATE ON "public"."categories" FOR EACH ROW EXECUTE FUNCTION "public"."update_modified_column"();



CREATE OR REPLACE TRIGGER "update_notifications_updated_at" BEFORE UPDATE ON "public"."notifications" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "update_shipments_updated_at" BEFORE UPDATE ON "public"."shipments" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "update_user_notifications_updated_at" BEFORE UPDATE ON "public"."user_notifications" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



ALTER TABLE ONLY "public"."audit_logs"
    ADD CONSTRAINT "audit_logs_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id");



ALTER TABLE ONLY "public"."cart_items"
    ADD CONSTRAINT "cart_items_product_id_fkey" FOREIGN KEY ("product_id") REFERENCES "public"."products"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."cart_items"
    ADD CONSTRAINT "cart_items_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."cart_items"
    ADD CONSTRAINT "cart_items_variant_id_fkey" FOREIGN KEY ("variant_id") REFERENCES "public"."product_variants"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."categories"
    ADD CONSTRAINT "categories_parent_id_fkey" FOREIGN KEY ("parent_id") REFERENCES "public"."categories"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."collection_products"
    ADD CONSTRAINT "collection_products_collection_id_fkey" FOREIGN KEY ("collection_id") REFERENCES "public"."collections"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."collection_products"
    ADD CONSTRAINT "collection_products_product_id_fkey" FOREIGN KEY ("product_id") REFERENCES "public"."products"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."coupon_categories"
    ADD CONSTRAINT "coupon_categories_coupon_id_fkey" FOREIGN KEY ("coupon_id") REFERENCES "public"."coupons"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."coupon_products"
    ADD CONSTRAINT "coupon_products_coupon_id_fkey" FOREIGN KEY ("coupon_id") REFERENCES "public"."coupons"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."coupon_usages"
    ADD CONSTRAINT "coupon_usages_coupon_id_fkey" FOREIGN KEY ("coupon_id") REFERENCES "public"."coupons"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."coupon_usages"
    ADD CONSTRAINT "coupon_usages_order_id_fkey" FOREIGN KEY ("order_id") REFERENCES "public"."orders"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."favorites"
    ADD CONSTRAINT "favorites_product_id_fkey" FOREIGN KEY ("product_id") REFERENCES "public"."products"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."order_items"
    ADD CONSTRAINT "fk_order_items_variants" FOREIGN KEY ("variant_id") REFERENCES "public"."product_variants"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."flash_sale_items"
    ADD CONSTRAINT "flash_sale_items_flash_sale_id_fkey" FOREIGN KEY ("flash_sale_id") REFERENCES "public"."flash_sales"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."flash_sale_items"
    ADD CONSTRAINT "flash_sale_items_product_id_fkey" FOREIGN KEY ("product_id") REFERENCES "public"."products"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."flash_sale_items"
    ADD CONSTRAINT "flash_sale_items_variant_id_fkey" FOREIGN KEY ("variant_id") REFERENCES "public"."product_variants"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."inventory_logs"
    ADD CONSTRAINT "inventory_logs_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."users"("id");



ALTER TABLE ONLY "public"."inventory_logs"
    ADD CONSTRAINT "inventory_logs_product_id_fkey" FOREIGN KEY ("product_id") REFERENCES "public"."products"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."inventory_logs"
    ADD CONSTRAINT "inventory_logs_variant_id_fkey" FOREIGN KEY ("variant_id") REFERENCES "public"."product_variants"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."loyalty_transactions"
    ADD CONSTRAINT "loyalty_transactions_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."order_items"
    ADD CONSTRAINT "order_items_order_id_fkey" FOREIGN KEY ("order_id") REFERENCES "public"."orders"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."order_items"
    ADD CONSTRAINT "order_items_product_id_fkey" FOREIGN KEY ("product_id") REFERENCES "public"."products"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."orders"
    ADD CONSTRAINT "orders_coupon_id_fkey" FOREIGN KEY ("coupon_id") REFERENCES "public"."coupons"("id");



ALTER TABLE ONLY "public"."orders"
    ADD CONSTRAINT "orders_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."payments"
    ADD CONSTRAINT "payments_order_id_fkey" FOREIGN KEY ("order_id") REFERENCES "public"."orders"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."product_analytics"
    ADD CONSTRAINT "product_analytics_product_id_fkey" FOREIGN KEY ("product_id") REFERENCES "public"."products"("id");



ALTER TABLE ONLY "public"."product_categories"
    ADD CONSTRAINT "product_categories_category_id_fkey" FOREIGN KEY ("category_id") REFERENCES "public"."categories"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."product_categories"
    ADD CONSTRAINT "product_categories_product_id_fkey" FOREIGN KEY ("product_id") REFERENCES "public"."products"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."product_images"
    ADD CONSTRAINT "product_images_product_id_fkey" FOREIGN KEY ("product_id") REFERENCES "public"."products"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."product_reviews"
    ADD CONSTRAINT "product_reviews_order_id_fkey" FOREIGN KEY ("order_id") REFERENCES "public"."orders"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."product_reviews"
    ADD CONSTRAINT "product_reviews_product_id_fkey" FOREIGN KEY ("product_id") REFERENCES "public"."products"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."product_reviews"
    ADD CONSTRAINT "product_reviews_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."product_variants"
    ADD CONSTRAINT "product_variants_product_id_fkey" FOREIGN KEY ("product_id") REFERENCES "public"."products"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."products"
    ADD CONSTRAINT "products_brand_id_fkey" FOREIGN KEY ("brand_id") REFERENCES "public"."brands"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."return_requests"
    ADD CONSTRAINT "return_requests_order_id_fkey" FOREIGN KEY ("order_id") REFERENCES "public"."orders"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."return_requests"
    ADD CONSTRAINT "return_requests_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."shipment_events"
    ADD CONSTRAINT "shipment_events_shipment_id_fkey" FOREIGN KEY ("shipment_id") REFERENCES "public"."shipments"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."shipments"
    ADD CONSTRAINT "shipments_order_id_fkey" FOREIGN KEY ("order_id") REFERENCES "public"."orders"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."user_addresses"
    ADD CONSTRAINT "user_addresses_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."user_notifications"
    ADD CONSTRAINT "user_notifications_notification_id_fkey" FOREIGN KEY ("notification_id") REFERENCES "public"."notifications"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."user_notifications"
    ADD CONSTRAINT "user_notifications_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."users"
    ADD CONSTRAINT "users_admin_role_slug_fkey" FOREIGN KEY ("admin_role_slug") REFERENCES "public"."admin_roles"("slug") ON DELETE SET NULL;



CREATE POLICY "Allow authenticated insert order items" ON "public"."order_items" FOR INSERT TO "authenticated" WITH CHECK (true);



CREATE POLICY "Allow authenticated insert orders" ON "public"."orders" FOR INSERT TO "authenticated" WITH CHECK (true);



CREATE POLICY "Anyone can read visible product reviews" ON "public"."product_reviews" FOR SELECT TO "authenticated", "anon" USING ((COALESCE("is_hidden", false) = false));



CREATE POLICY "Public can read active collections" ON "public"."collections" FOR SELECT TO "authenticated", "anon" USING (("is_active" = true));



CREATE POLICY "Public can read active flash sales" ON "public"."flash_sales" FOR SELECT TO "authenticated", "anon" USING ((COALESCE("is_active", true) = true));



CREATE POLICY "Public can read active notifications" ON "public"."notifications" FOR SELECT TO "authenticated", "anon" USING (((COALESCE("is_active", true) = true) AND (("start_at" IS NULL) OR ("start_at" <= "now"())) AND (("end_at" IS NULL) OR ("end_at" >= "now"()))));



CREATE POLICY "Public can read active products" ON "public"."products" FOR SELECT TO "authenticated", "anon" USING (((COALESCE("is_active", true) = true) AND ("deleted_at" IS NULL)));



CREATE POLICY "Public can read brands" ON "public"."brands" FOR SELECT TO "authenticated", "anon" USING (true);



CREATE POLICY "Public can read categories" ON "public"."categories" FOR SELECT TO "authenticated", "anon" USING (true);



CREATE POLICY "Public can read collection products" ON "public"."collection_products" FOR SELECT TO "authenticated", "anon" USING (true);



CREATE POLICY "Public can read coupon categories" ON "public"."coupon_categories" FOR SELECT TO "authenticated", "anon" USING (true);



CREATE POLICY "Public can read coupon products" ON "public"."coupon_products" FOR SELECT TO "authenticated", "anon" USING (true);



CREATE POLICY "Public can read coupons" ON "public"."coupons" FOR SELECT TO "authenticated", "anon" USING ((COALESCE("is_active", true) = true));



CREATE POLICY "Public can read flash sale items" ON "public"."flash_sale_items" FOR SELECT TO "authenticated", "anon" USING (true);



CREATE POLICY "Public can read product categories" ON "public"."product_categories" FOR SELECT TO "authenticated", "anon" USING (true);



CREATE POLICY "Public can read product images" ON "public"."product_images" FOR SELECT TO "authenticated", "anon" USING (true);



CREATE POLICY "Public can read product variants" ON "public"."product_variants" FOR SELECT TO "authenticated", "anon" USING (true);



CREATE POLICY "Public can read shipping providers" ON "public"."shipping_providers" FOR SELECT TO "authenticated", "anon" USING (("is_active" = true));



CREATE POLICY "Public can read store settings" ON "public"."store_settings" FOR SELECT TO "authenticated", "anon" USING (true);



CREATE POLICY "Users can create order items for own orders" ON "public"."order_items" FOR INSERT TO "authenticated" WITH CHECK ((EXISTS ( SELECT 1
   FROM "public"."orders" "o"
  WHERE (("o"."id" = "order_items"."order_id") AND ("o"."user_id" = "auth"."uid"())))));



CREATE POLICY "Users can create own orders" ON "public"."orders" FOR INSERT TO "authenticated" WITH CHECK (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can create own product reviews" ON "public"."product_reviews" FOR INSERT TO "authenticated" WITH CHECK (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can create own return requests" ON "public"."return_requests" FOR INSERT TO "authenticated" WITH CHECK (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can delete own addresses" ON "public"."user_addresses" FOR DELETE TO "authenticated" USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can delete own cart items" ON "public"."cart_items" FOR DELETE TO "authenticated" USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can delete own favorites" ON "public"."favorites" FOR DELETE TO "authenticated" USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can insert own addresses" ON "public"."user_addresses" FOR INSERT TO "authenticated" WITH CHECK (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can insert own cart items" ON "public"."cart_items" FOR INSERT TO "authenticated" WITH CHECK (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can insert own favorites" ON "public"."favorites" FOR INSERT TO "authenticated" WITH CHECK (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can update own addresses" ON "public"."user_addresses" FOR UPDATE TO "authenticated" USING (("auth"."uid"() = "user_id")) WITH CHECK (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can update own cart items" ON "public"."cart_items" FOR UPDATE TO "authenticated" USING (("auth"."uid"() = "user_id")) WITH CHECK (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can update own notifications" ON "public"."user_notifications" FOR UPDATE TO "authenticated" USING (("auth"."uid"() = "user_id")) WITH CHECK (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can view own addresses" ON "public"."user_addresses" FOR SELECT TO "authenticated" USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can view own cart items" ON "public"."cart_items" FOR SELECT TO "authenticated" USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can view own favorites" ON "public"."favorites" FOR SELECT TO "authenticated" USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can view own notifications" ON "public"."user_notifications" FOR SELECT TO "authenticated" USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can view own order items" ON "public"."order_items" FOR SELECT TO "authenticated" USING ((EXISTS ( SELECT 1
   FROM "public"."orders" "o"
  WHERE (("o"."id" = "order_items"."order_id") AND ("o"."user_id" = "auth"."uid"())))));



CREATE POLICY "Users can view own orders" ON "public"."orders" FOR SELECT TO "authenticated" USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can view own return requests" ON "public"."return_requests" FOR SELECT TO "authenticated" USING (("auth"."uid"() = "user_id"));



ALTER TABLE "public"."admin_roles" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."audit_logs" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."brands" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."carrier_status_mapping" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."cart_items" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."categories" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."collection_products" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."collections" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."coupon_categories" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."coupon_products" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."coupon_usages" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."coupons" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."customers" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."favorites" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."flash_sale_items" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."flash_sales" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."inventory_logs" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."loyalty_transactions" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."notifications" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."order_items" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."orders" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."payments" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."product_analytics" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."product_categories" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."product_images" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."product_reviews" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."product_variants" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."products" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."return_requests" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "service_role_full_access" ON "public"."user_notifications" TO "service_role" USING (true) WITH CHECK (true);



ALTER TABLE "public"."shipment_events" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."shipments" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."shipping_configs" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."shipping_providers" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."store_settings" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."user_addresses" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."user_notifications" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."users" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."webhook_logs" ENABLE ROW LEVEL SECURITY;




ALTER PUBLICATION "supabase_realtime" OWNER TO "postgres";


GRANT USAGE ON SCHEMA "public" TO "postgres";
GRANT USAGE ON SCHEMA "public" TO "anon";
GRANT USAGE ON SCHEMA "public" TO "authenticated";
GRANT USAGE ON SCHEMA "public" TO "service_role";






















































































































































GRANT ALL ON FUNCTION "public"."add_item_to_cart"("p_user_id" "uuid", "p_product_id" "uuid", "p_quantity" integer, "p_size" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."add_item_to_cart"("p_user_id" "uuid", "p_product_id" "uuid", "p_quantity" integer, "p_size" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."add_item_to_cart"("p_user_id" "uuid", "p_product_id" "uuid", "p_quantity" integer, "p_size" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."apply_coupon"("p_code" "text", "p_user_id" "uuid", "p_order_id" "uuid") TO "anon";
GRANT ALL ON FUNCTION "public"."apply_coupon"("p_code" "text", "p_user_id" "uuid", "p_order_id" "uuid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."apply_coupon"("p_code" "text", "p_user_id" "uuid", "p_order_id" "uuid") TO "service_role";



GRANT ALL ON FUNCTION "public"."fan_out_notification"("p_notification_id" "uuid") TO "anon";
GRANT ALL ON FUNCTION "public"."fan_out_notification"("p_notification_id" "uuid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."fan_out_notification"("p_notification_id" "uuid") TO "service_role";



GRANT ALL ON FUNCTION "public"."get_cart_total_quantity"("p_user_id" "uuid") TO "anon";
GRANT ALL ON FUNCTION "public"."get_cart_total_quantity"("p_user_id" "uuid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_cart_total_quantity"("p_user_id" "uuid") TO "service_role";



GRANT ALL ON FUNCTION "public"."get_product_count_by_category"() TO "anon";
GRANT ALL ON FUNCTION "public"."get_product_count_by_category"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_product_count_by_category"() TO "service_role";



GRANT ALL ON FUNCTION "public"."get_unread_notification_count"("p_user_id" "uuid") TO "anon";
GRANT ALL ON FUNCTION "public"."get_unread_notification_count"("p_user_id" "uuid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_unread_notification_count"("p_user_id" "uuid") TO "service_role";



GRANT ALL ON FUNCTION "public"."is_user_in_segment"("p_user_id" "uuid", "p_segment" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."is_user_in_segment"("p_user_id" "uuid", "p_segment" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."is_user_in_segment"("p_user_id" "uuid", "p_segment" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."log_product_event"("p_product_id" "uuid", "p_channel" "text", "p_source" "text", "p_event_type" "text", "p_revenue" numeric, "p_qty" integer) TO "anon";
GRANT ALL ON FUNCTION "public"."log_product_event"("p_product_id" "uuid", "p_channel" "text", "p_source" "text", "p_event_type" "text", "p_revenue" numeric, "p_qty" integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."log_product_event"("p_product_id" "uuid", "p_channel" "text", "p_source" "text", "p_event_type" "text", "p_revenue" numeric, "p_qty" integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."rls_auto_enable"() TO "anon";
GRANT ALL ON FUNCTION "public"."rls_auto_enable"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."rls_auto_enable"() TO "service_role";



GRANT ALL ON FUNCTION "public"."sync_product_stock"() TO "anon";
GRANT ALL ON FUNCTION "public"."sync_product_stock"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."sync_product_stock"() TO "service_role";



GRANT ALL ON FUNCTION "public"."update_modified_column"() TO "anon";
GRANT ALL ON FUNCTION "public"."update_modified_column"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."update_modified_column"() TO "service_role";



GRANT ALL ON FUNCTION "public"."update_updated_at_column"() TO "anon";
GRANT ALL ON FUNCTION "public"."update_updated_at_column"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."update_updated_at_column"() TO "service_role";



GRANT ALL ON FUNCTION "public"."update_user_points_balance"() TO "anon";
GRANT ALL ON FUNCTION "public"."update_user_points_balance"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."update_user_points_balance"() TO "service_role";


















GRANT ALL ON TABLE "public"."admin_roles" TO "service_role";



GRANT ALL ON TABLE "public"."audit_logs" TO "service_role";



GRANT ALL ON TABLE "public"."brands" TO "service_role";
GRANT SELECT ON TABLE "public"."brands" TO "anon";
GRANT SELECT ON TABLE "public"."brands" TO "authenticated";



GRANT ALL ON TABLE "public"."carrier_status_mapping" TO "service_role";



GRANT ALL ON SEQUENCE "public"."carrier_status_mapping_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."carrier_status_mapping_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."carrier_status_mapping_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."cart_items" TO "service_role";
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE "public"."cart_items" TO "authenticated";



GRANT ALL ON TABLE "public"."categories" TO "service_role";
GRANT SELECT ON TABLE "public"."categories" TO "anon";
GRANT SELECT ON TABLE "public"."categories" TO "authenticated";



GRANT ALL ON TABLE "public"."collection_products" TO "service_role";
GRANT SELECT ON TABLE "public"."collection_products" TO "anon";
GRANT SELECT ON TABLE "public"."collection_products" TO "authenticated";



GRANT ALL ON TABLE "public"."collections" TO "service_role";
GRANT SELECT ON TABLE "public"."collections" TO "anon";
GRANT SELECT ON TABLE "public"."collections" TO "authenticated";



GRANT ALL ON TABLE "public"."coupon_categories" TO "service_role";
GRANT SELECT ON TABLE "public"."coupon_categories" TO "anon";
GRANT SELECT ON TABLE "public"."coupon_categories" TO "authenticated";



GRANT ALL ON TABLE "public"."coupon_products" TO "service_role";
GRANT SELECT ON TABLE "public"."coupon_products" TO "anon";
GRANT SELECT ON TABLE "public"."coupon_products" TO "authenticated";



GRANT ALL ON TABLE "public"."coupon_usages" TO "service_role";



GRANT ALL ON TABLE "public"."coupons" TO "service_role";
GRANT SELECT ON TABLE "public"."coupons" TO "anon";
GRANT SELECT ON TABLE "public"."coupons" TO "authenticated";



GRANT ALL ON TABLE "public"."customers" TO "service_role";



GRANT ALL ON TABLE "public"."favorites" TO "service_role";
GRANT SELECT,INSERT,DELETE ON TABLE "public"."favorites" TO "authenticated";



GRANT ALL ON TABLE "public"."flash_sale_items" TO "service_role";
GRANT SELECT ON TABLE "public"."flash_sale_items" TO "anon";
GRANT SELECT ON TABLE "public"."flash_sale_items" TO "authenticated";



GRANT ALL ON TABLE "public"."flash_sales" TO "service_role";
GRANT SELECT ON TABLE "public"."flash_sales" TO "anon";
GRANT SELECT ON TABLE "public"."flash_sales" TO "authenticated";



GRANT ALL ON TABLE "public"."inventory_logs" TO "service_role";



GRANT ALL ON TABLE "public"."loyalty_transactions" TO "service_role";



GRANT ALL ON TABLE "public"."notifications" TO "service_role";
GRANT SELECT ON TABLE "public"."notifications" TO "anon";
GRANT SELECT ON TABLE "public"."notifications" TO "authenticated";



GRANT ALL ON TABLE "public"."order_items" TO "service_role";
GRANT SELECT,INSERT ON TABLE "public"."order_items" TO "authenticated";



GRANT ALL ON TABLE "public"."orders" TO "service_role";
GRANT SELECT,INSERT ON TABLE "public"."orders" TO "authenticated";



GRANT ALL ON TABLE "public"."payments" TO "service_role";



GRANT ALL ON TABLE "public"."product_analytics" TO "service_role";



GRANT ALL ON TABLE "public"."product_categories" TO "service_role";
GRANT SELECT ON TABLE "public"."product_categories" TO "anon";
GRANT SELECT ON TABLE "public"."product_categories" TO "authenticated";



GRANT ALL ON TABLE "public"."product_images" TO "service_role";
GRANT SELECT ON TABLE "public"."product_images" TO "anon";
GRANT SELECT ON TABLE "public"."product_images" TO "authenticated";



GRANT ALL ON TABLE "public"."product_reviews" TO "service_role";
GRANT SELECT,INSERT ON TABLE "public"."product_reviews" TO "authenticated";
GRANT SELECT ON TABLE "public"."product_reviews" TO "anon";



GRANT ALL ON TABLE "public"."product_variants" TO "service_role";
GRANT SELECT ON TABLE "public"."product_variants" TO "anon";
GRANT SELECT ON TABLE "public"."product_variants" TO "authenticated";



GRANT ALL ON TABLE "public"."products" TO "service_role";
GRANT SELECT ON TABLE "public"."products" TO "anon";
GRANT SELECT ON TABLE "public"."products" TO "authenticated";



GRANT ALL ON TABLE "public"."return_requests" TO "service_role";
GRANT SELECT,INSERT ON TABLE "public"."return_requests" TO "authenticated";



GRANT ALL ON TABLE "public"."shipment_events" TO "service_role";



GRANT ALL ON TABLE "public"."shipments" TO "service_role";



GRANT ALL ON TABLE "public"."shipping_configs" TO "service_role";



GRANT ALL ON TABLE "public"."shipping_providers" TO "service_role";
GRANT SELECT ON TABLE "public"."shipping_providers" TO "anon";
GRANT SELECT ON TABLE "public"."shipping_providers" TO "authenticated";



GRANT ALL ON TABLE "public"."store_settings" TO "service_role";
GRANT SELECT ON TABLE "public"."store_settings" TO "anon";
GRANT SELECT ON TABLE "public"."store_settings" TO "authenticated";



GRANT ALL ON TABLE "public"."user_addresses" TO "service_role";
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE "public"."user_addresses" TO "authenticated";



GRANT ALL ON TABLE "public"."user_notifications" TO "service_role";
GRANT SELECT,UPDATE ON TABLE "public"."user_notifications" TO "authenticated";



GRANT ALL ON TABLE "public"."users" TO "service_role";



GRANT ALL ON TABLE "public"."webhook_logs" TO "service_role";









ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "service_role";




































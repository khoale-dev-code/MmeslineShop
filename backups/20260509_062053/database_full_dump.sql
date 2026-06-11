--
-- PostgreSQL database dump
--

\restrict bikEs4g4SUDgbsWxHfXss9PMg6pbYyXbsZozlZDy9xrDjDwBclPwS8fO87OvKOe

-- Dumped from database version 17.6
-- Dumped by pg_dump version 18.3

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

DROP EVENT TRIGGER IF EXISTS pgrst_drop_watch;
DROP EVENT TRIGGER IF EXISTS pgrst_ddl_watch;
DROP EVENT TRIGGER IF EXISTS issue_pg_net_access;
DROP EVENT TRIGGER IF EXISTS issue_pg_graphql_access;
DROP EVENT TRIGGER IF EXISTS issue_pg_cron_access;
DROP EVENT TRIGGER IF EXISTS issue_graphql_placeholder;
DROP EVENT TRIGGER IF EXISTS ensure_rls;
DROP PUBLICATION IF EXISTS supabase_realtime;
DROP POLICY IF EXISTS allow_insert_analytics ON public.product_analytics;
DROP POLICY IF EXISTS "Enable insert for all users" ON public.product_analytics;
DROP POLICY IF EXISTS "Enable all access for all users" ON public.system_settings;
DROP POLICY IF EXISTS "Enable all access for all users" ON public.shipments;
DROP POLICY IF EXISTS "Enable all access for all users" ON public.shipment_events;
DROP POLICY IF EXISTS "Backend only write" ON public.product_analytics;
DROP POLICY IF EXISTS "Allow read roles for all" ON public.roles;
DROP POLICY IF EXISTS "Allow read own user_roles" ON public.user_roles;
DROP POLICY IF EXISTS "Allow insert for authenticated users" ON public.coupon_usages;
DROP POLICY IF EXISTS "Allow insert analytics" ON public.product_analytics;
DROP POLICY IF EXISTS "Allow all for admin service" ON public.shipping_providers;
ALTER TABLE IF EXISTS ONLY storage.vector_indexes DROP CONSTRAINT IF EXISTS vector_indexes_bucket_id_fkey;
ALTER TABLE IF EXISTS ONLY storage.s3_multipart_uploads_parts DROP CONSTRAINT IF EXISTS s3_multipart_uploads_parts_upload_id_fkey;
ALTER TABLE IF EXISTS ONLY storage.s3_multipart_uploads_parts DROP CONSTRAINT IF EXISTS s3_multipart_uploads_parts_bucket_id_fkey;
ALTER TABLE IF EXISTS ONLY storage.s3_multipart_uploads DROP CONSTRAINT IF EXISTS s3_multipart_uploads_bucket_id_fkey;
ALTER TABLE IF EXISTS ONLY storage.objects DROP CONSTRAINT IF EXISTS "objects_bucketId_fkey";
ALTER TABLE IF EXISTS ONLY public.user_roles DROP CONSTRAINT IF EXISTS user_roles_user_id_fkey;
ALTER TABLE IF EXISTS ONLY public.user_roles DROP CONSTRAINT IF EXISTS user_roles_tenant_id_fkey;
ALTER TABLE IF EXISTS ONLY public.user_roles DROP CONSTRAINT IF EXISTS user_roles_role_id_fkey;
ALTER TABLE IF EXISTS ONLY public.user_permissions DROP CONSTRAINT IF EXISTS user_permissions_user_id_fkey;
ALTER TABLE IF EXISTS ONLY public.user_permissions DROP CONSTRAINT IF EXISTS user_permissions_permission_id_fkey;
ALTER TABLE IF EXISTS ONLY public.user_addresses DROP CONSTRAINT IF EXISTS user_addresses_user_id_fkey;
ALTER TABLE IF EXISTS ONLY public.shipments DROP CONSTRAINT IF EXISTS shipments_order_id_fkey;
ALTER TABLE IF EXISTS ONLY public.shipment_events DROP CONSTRAINT IF EXISTS shipment_events_shipment_id_fkey;
ALTER TABLE IF EXISTS ONLY public.roles DROP CONSTRAINT IF EXISTS roles_tenant_id_fkey;
ALTER TABLE IF EXISTS ONLY public.roles DROP CONSTRAINT IF EXISTS roles_parent_id_fkey;
ALTER TABLE IF EXISTS ONLY public.role_permissions DROP CONSTRAINT IF EXISTS role_permissions_role_id_fkey;
ALTER TABLE IF EXISTS ONLY public.role_permissions DROP CONSTRAINT IF EXISTS role_permissions_permission_id_fkey;
ALTER TABLE IF EXISTS ONLY public.return_requests DROP CONSTRAINT IF EXISTS return_requests_user_id_fkey;
ALTER TABLE IF EXISTS ONLY public.return_requests DROP CONSTRAINT IF EXISTS return_requests_order_id_fkey;
ALTER TABLE IF EXISTS ONLY public.products DROP CONSTRAINT IF EXISTS products_category_id_fkey;
ALTER TABLE IF EXISTS ONLY public.products DROP CONSTRAINT IF EXISTS products_brand_id_fkey;
ALTER TABLE IF EXISTS ONLY public.product_variants DROP CONSTRAINT IF EXISTS product_variants_product_id_fkey;
ALTER TABLE IF EXISTS ONLY public.product_reviews DROP CONSTRAINT IF EXISTS product_reviews_user_id_fkey;
ALTER TABLE IF EXISTS ONLY public.product_reviews DROP CONSTRAINT IF EXISTS product_reviews_product_id_fkey;
ALTER TABLE IF EXISTS ONLY public.product_reviews DROP CONSTRAINT IF EXISTS product_reviews_order_id_fkey;
ALTER TABLE IF EXISTS ONLY public.product_images DROP CONSTRAINT IF EXISTS product_images_product_id_fkey;
ALTER TABLE IF EXISTS ONLY public.product_analytics DROP CONSTRAINT IF EXISTS product_analytics_product_id_fkey;
ALTER TABLE IF EXISTS ONLY public.permissions DROP CONSTRAINT IF EXISTS permissions_group_id_fkey;
ALTER TABLE IF EXISTS ONLY public.payments DROP CONSTRAINT IF EXISTS payments_order_id_fkey;
ALTER TABLE IF EXISTS ONLY public.orders DROP CONSTRAINT IF EXISTS orders_user_id_fkey;
ALTER TABLE IF EXISTS ONLY public.orders DROP CONSTRAINT IF EXISTS orders_coupon_id_fkey;
ALTER TABLE IF EXISTS ONLY public.order_items DROP CONSTRAINT IF EXISTS order_items_product_id_fkey;
ALTER TABLE IF EXISTS ONLY public.order_items DROP CONSTRAINT IF EXISTS order_items_order_id_fkey;
ALTER TABLE IF EXISTS ONLY public.inventory_logs DROP CONSTRAINT IF EXISTS inventory_logs_variant_id_fkey;
ALTER TABLE IF EXISTS ONLY public.inventory_logs DROP CONSTRAINT IF EXISTS inventory_logs_product_id_fkey;
ALTER TABLE IF EXISTS ONLY public.inventory_logs DROP CONSTRAINT IF EXISTS inventory_logs_created_by_fkey;
ALTER TABLE IF EXISTS ONLY public.flash_sale_items DROP CONSTRAINT IF EXISTS flash_sale_items_variant_id_fkey;
ALTER TABLE IF EXISTS ONLY public.flash_sale_items DROP CONSTRAINT IF EXISTS flash_sale_items_product_id_fkey;
ALTER TABLE IF EXISTS ONLY public.flash_sale_items DROP CONSTRAINT IF EXISTS flash_sale_items_flash_sale_id_fkey;
ALTER TABLE IF EXISTS ONLY public.order_items DROP CONSTRAINT IF EXISTS fk_order_items_variants;
ALTER TABLE IF EXISTS ONLY public.favorites DROP CONSTRAINT IF EXISTS favorites_product_id_fkey;
ALTER TABLE IF EXISTS ONLY public.coupon_usages DROP CONSTRAINT IF EXISTS coupon_usages_order_id_fkey;
ALTER TABLE IF EXISTS ONLY public.coupon_usages DROP CONSTRAINT IF EXISTS coupon_usages_coupon_id_fkey;
ALTER TABLE IF EXISTS ONLY public.coupon_segments DROP CONSTRAINT IF EXISTS coupon_segments_coupon_id_fkey;
ALTER TABLE IF EXISTS ONLY public.coupon_products DROP CONSTRAINT IF EXISTS coupon_products_coupon_id_fkey;
ALTER TABLE IF EXISTS ONLY public.coupon_categories DROP CONSTRAINT IF EXISTS coupon_categories_coupon_id_fkey;
ALTER TABLE IF EXISTS ONLY public.categories DROP CONSTRAINT IF EXISTS categories_parent_id_fkey;
ALTER TABLE IF EXISTS ONLY public.cart_items DROP CONSTRAINT IF EXISTS cart_items_variant_id_fkey;
ALTER TABLE IF EXISTS ONLY public.cart_items DROP CONSTRAINT IF EXISTS cart_items_user_id_fkey;
ALTER TABLE IF EXISTS ONLY public.cart_items DROP CONSTRAINT IF EXISTS cart_items_product_id_fkey;
ALTER TABLE IF EXISTS ONLY public.audit_logs DROP CONSTRAINT IF EXISTS audit_logs_user_id_fkey;
ALTER TABLE IF EXISTS ONLY public.audit_logs DROP CONSTRAINT IF EXISTS audit_logs_tenant_id_fkey;
ALTER TABLE IF EXISTS ONLY auth.webauthn_credentials DROP CONSTRAINT IF EXISTS webauthn_credentials_user_id_fkey;
ALTER TABLE IF EXISTS ONLY auth.webauthn_challenges DROP CONSTRAINT IF EXISTS webauthn_challenges_user_id_fkey;
ALTER TABLE IF EXISTS ONLY auth.sso_domains DROP CONSTRAINT IF EXISTS sso_domains_sso_provider_id_fkey;
ALTER TABLE IF EXISTS ONLY auth.sessions DROP CONSTRAINT IF EXISTS sessions_user_id_fkey;
ALTER TABLE IF EXISTS ONLY auth.sessions DROP CONSTRAINT IF EXISTS sessions_oauth_client_id_fkey;
ALTER TABLE IF EXISTS ONLY auth.saml_relay_states DROP CONSTRAINT IF EXISTS saml_relay_states_sso_provider_id_fkey;
ALTER TABLE IF EXISTS ONLY auth.saml_relay_states DROP CONSTRAINT IF EXISTS saml_relay_states_flow_state_id_fkey;
ALTER TABLE IF EXISTS ONLY auth.saml_providers DROP CONSTRAINT IF EXISTS saml_providers_sso_provider_id_fkey;
ALTER TABLE IF EXISTS ONLY auth.refresh_tokens DROP CONSTRAINT IF EXISTS refresh_tokens_session_id_fkey;
ALTER TABLE IF EXISTS ONLY auth.one_time_tokens DROP CONSTRAINT IF EXISTS one_time_tokens_user_id_fkey;
ALTER TABLE IF EXISTS ONLY auth.oauth_consents DROP CONSTRAINT IF EXISTS oauth_consents_user_id_fkey;
ALTER TABLE IF EXISTS ONLY auth.oauth_consents DROP CONSTRAINT IF EXISTS oauth_consents_client_id_fkey;
ALTER TABLE IF EXISTS ONLY auth.oauth_authorizations DROP CONSTRAINT IF EXISTS oauth_authorizations_user_id_fkey;
ALTER TABLE IF EXISTS ONLY auth.oauth_authorizations DROP CONSTRAINT IF EXISTS oauth_authorizations_client_id_fkey;
ALTER TABLE IF EXISTS ONLY auth.mfa_factors DROP CONSTRAINT IF EXISTS mfa_factors_user_id_fkey;
ALTER TABLE IF EXISTS ONLY auth.mfa_challenges DROP CONSTRAINT IF EXISTS mfa_challenges_auth_factor_id_fkey;
ALTER TABLE IF EXISTS ONLY auth.mfa_amr_claims DROP CONSTRAINT IF EXISTS mfa_amr_claims_session_id_fkey;
ALTER TABLE IF EXISTS ONLY auth.identities DROP CONSTRAINT IF EXISTS identities_user_id_fkey;
DROP TRIGGER IF EXISTS update_objects_updated_at ON storage.objects;
DROP TRIGGER IF EXISTS protect_objects_delete ON storage.objects;
DROP TRIGGER IF EXISTS protect_buckets_delete ON storage.buckets;
DROP TRIGGER IF EXISTS enforce_bucket_name_length_trigger ON storage.buckets;
DROP TRIGGER IF EXISTS tr_check_filters ON realtime.subscription;
DROP TRIGGER IF EXISTS update_shipments_updated_at ON public.shipments;
DROP TRIGGER IF EXISTS update_categories_modtime ON public.categories;
DROP INDEX IF EXISTS storage.vector_indexes_name_bucket_id_idx;
DROP INDEX IF EXISTS storage.name_prefix_search;
DROP INDEX IF EXISTS storage.idx_objects_bucket_id_name_lower;
DROP INDEX IF EXISTS storage.idx_objects_bucket_id_name;
DROP INDEX IF EXISTS storage.idx_multipart_uploads_list;
DROP INDEX IF EXISTS storage.buckets_analytics_unique_name_idx;
DROP INDEX IF EXISTS storage.bucketid_objname;
DROP INDEX IF EXISTS storage.bname;
DROP INDEX IF EXISTS realtime.subscription_subscription_id_entity_filters_action_filter_key;
DROP INDEX IF EXISTS realtime.messages_inserted_at_topic_index;
DROP INDEX IF EXISTS realtime.ix_realtime_subscription_entity;
DROP INDEX IF EXISTS public.textsearch_idx;
DROP INDEX IF EXISTS public.idx_webhook_logs_provider_created;
DROP INDEX IF EXISTS public.idx_variants_product;
DROP INDEX IF EXISTS public.idx_user_addresses_user_id;
DROP INDEX IF EXISTS public.idx_shipments_tracking_code;
DROP INDEX IF EXISTS public.idx_shipments_status_created;
DROP INDEX IF EXISTS public.idx_shipments_raw_response;
DROP INDEX IF EXISTS public.idx_return_requests_user;
DROP INDEX IF EXISTS public.idx_return_requests_status;
DROP INDEX IF EXISTS public.idx_return_requests_order;
DROP INDEX IF EXISTS public.idx_products_slug;
DROP INDEX IF EXISTS public.idx_products_is_active;
DROP INDEX IF EXISTS public.idx_products_featured;
DROP INDEX IF EXISTS public.idx_products_category_id;
DROP INDEX IF EXISTS public.idx_products_category;
DROP INDEX IF EXISTS public.idx_product_images_product;
DROP INDEX IF EXISTS public.idx_pa_product;
DROP INDEX IF EXISTS public.idx_pa_date;
DROP INDEX IF EXISTS public.idx_pa_channel;
DROP INDEX IF EXISTS public.idx_orders_user_id;
DROP INDEX IF EXISTS public.idx_orders_user;
DROP INDEX IF EXISTS public.idx_orders_status;
DROP INDEX IF EXISTS public.idx_orders_shipping_address;
DROP INDEX IF EXISTS public.idx_orders_created_at;
DROP INDEX IF EXISTS public.idx_order_items_order_id;
DROP INDEX IF EXISTS public.idx_order_items_order;
DROP INDEX IF EXISTS public.idx_favorites_user_id;
DROP INDEX IF EXISTS public.idx_favorites_user;
DROP INDEX IF EXISTS public.idx_favorites_product;
DROP INDEX IF EXISTS public.idx_coupons_active;
DROP INDEX IF EXISTS public.idx_coupon_usages_user;
DROP INDEX IF EXISTS public.idx_coupon_products;
DROP INDEX IF EXISTS public.idx_coupon_categories;
DROP INDEX IF EXISTS public.idx_cart_user;
DROP INDEX IF EXISTS public.idx_cart_items_user_id;
DROP INDEX IF EXISTS public.idx_audit_logs_user_action;
DROP INDEX IF EXISTS public.idx_audit_logs_table_record;
DROP INDEX IF EXISTS public.idx_audit_logs_old_values;
DROP INDEX IF EXISTS public.idx_audit_logs_new_values;
DROP INDEX IF EXISTS auth.webauthn_credentials_user_id_idx;
DROP INDEX IF EXISTS auth.webauthn_credentials_credential_id_key;
DROP INDEX IF EXISTS auth.webauthn_challenges_user_id_idx;
DROP INDEX IF EXISTS auth.webauthn_challenges_expires_at_idx;
DROP INDEX IF EXISTS auth.users_is_anonymous_idx;
DROP INDEX IF EXISTS auth.users_instance_id_idx;
DROP INDEX IF EXISTS auth.users_instance_id_email_idx;
DROP INDEX IF EXISTS auth.users_email_partial_key;
DROP INDEX IF EXISTS auth.user_id_created_at_idx;
DROP INDEX IF EXISTS auth.unique_phone_factor_per_user;
DROP INDEX IF EXISTS auth.sso_providers_resource_id_pattern_idx;
DROP INDEX IF EXISTS auth.sso_providers_resource_id_idx;
DROP INDEX IF EXISTS auth.sso_domains_sso_provider_id_idx;
DROP INDEX IF EXISTS auth.sso_domains_domain_idx;
DROP INDEX IF EXISTS auth.sessions_user_id_idx;
DROP INDEX IF EXISTS auth.sessions_oauth_client_id_idx;
DROP INDEX IF EXISTS auth.sessions_not_after_idx;
DROP INDEX IF EXISTS auth.saml_relay_states_sso_provider_id_idx;
DROP INDEX IF EXISTS auth.saml_relay_states_for_email_idx;
DROP INDEX IF EXISTS auth.saml_relay_states_created_at_idx;
DROP INDEX IF EXISTS auth.saml_providers_sso_provider_id_idx;
DROP INDEX IF EXISTS auth.refresh_tokens_updated_at_idx;
DROP INDEX IF EXISTS auth.refresh_tokens_session_id_revoked_idx;
DROP INDEX IF EXISTS auth.refresh_tokens_parent_idx;
DROP INDEX IF EXISTS auth.refresh_tokens_instance_id_user_id_idx;
DROP INDEX IF EXISTS auth.refresh_tokens_instance_id_idx;
DROP INDEX IF EXISTS auth.recovery_token_idx;
DROP INDEX IF EXISTS auth.reauthentication_token_idx;
DROP INDEX IF EXISTS auth.one_time_tokens_user_id_token_type_key;
DROP INDEX IF EXISTS auth.one_time_tokens_token_hash_hash_idx;
DROP INDEX IF EXISTS auth.one_time_tokens_relates_to_hash_idx;
DROP INDEX IF EXISTS auth.oauth_consents_user_order_idx;
DROP INDEX IF EXISTS auth.oauth_consents_active_user_client_idx;
DROP INDEX IF EXISTS auth.oauth_consents_active_client_idx;
DROP INDEX IF EXISTS auth.oauth_clients_deleted_at_idx;
DROP INDEX IF EXISTS auth.oauth_auth_pending_exp_idx;
DROP INDEX IF EXISTS auth.mfa_factors_user_id_idx;
DROP INDEX IF EXISTS auth.mfa_factors_user_friendly_name_unique;
DROP INDEX IF EXISTS auth.mfa_challenge_created_at_idx;
DROP INDEX IF EXISTS auth.idx_users_name;
DROP INDEX IF EXISTS auth.idx_users_last_sign_in_at_desc;
DROP INDEX IF EXISTS auth.idx_users_email;
DROP INDEX IF EXISTS auth.idx_users_created_at_desc;
DROP INDEX IF EXISTS auth.idx_user_id_auth_method;
DROP INDEX IF EXISTS auth.idx_oauth_client_states_created_at;
DROP INDEX IF EXISTS auth.idx_auth_code;
DROP INDEX IF EXISTS auth.identities_user_id_idx;
DROP INDEX IF EXISTS auth.identities_email_idx;
DROP INDEX IF EXISTS auth.flow_state_created_at_idx;
DROP INDEX IF EXISTS auth.factor_id_created_at_idx;
DROP INDEX IF EXISTS auth.email_change_token_new_idx;
DROP INDEX IF EXISTS auth.email_change_token_current_idx;
DROP INDEX IF EXISTS auth.custom_oauth_providers_provider_type_idx;
DROP INDEX IF EXISTS auth.custom_oauth_providers_identifier_idx;
DROP INDEX IF EXISTS auth.custom_oauth_providers_enabled_idx;
DROP INDEX IF EXISTS auth.custom_oauth_providers_created_at_idx;
DROP INDEX IF EXISTS auth.confirmation_token_idx;
DROP INDEX IF EXISTS auth.audit_logs_instance_id_idx;
ALTER TABLE IF EXISTS ONLY storage.vector_indexes DROP CONSTRAINT IF EXISTS vector_indexes_pkey;
ALTER TABLE IF EXISTS ONLY storage.s3_multipart_uploads DROP CONSTRAINT IF EXISTS s3_multipart_uploads_pkey;
ALTER TABLE IF EXISTS ONLY storage.s3_multipart_uploads_parts DROP CONSTRAINT IF EXISTS s3_multipart_uploads_parts_pkey;
ALTER TABLE IF EXISTS ONLY storage.objects DROP CONSTRAINT IF EXISTS objects_pkey;
ALTER TABLE IF EXISTS ONLY storage.migrations DROP CONSTRAINT IF EXISTS migrations_pkey;
ALTER TABLE IF EXISTS ONLY storage.migrations DROP CONSTRAINT IF EXISTS migrations_name_key;
ALTER TABLE IF EXISTS ONLY storage.buckets_vectors DROP CONSTRAINT IF EXISTS buckets_vectors_pkey;
ALTER TABLE IF EXISTS ONLY storage.buckets DROP CONSTRAINT IF EXISTS buckets_pkey;
ALTER TABLE IF EXISTS ONLY storage.buckets_analytics DROP CONSTRAINT IF EXISTS buckets_analytics_pkey;
ALTER TABLE IF EXISTS ONLY realtime.schema_migrations DROP CONSTRAINT IF EXISTS schema_migrations_pkey;
ALTER TABLE IF EXISTS ONLY realtime.subscription DROP CONSTRAINT IF EXISTS pk_subscription;
ALTER TABLE IF EXISTS ONLY realtime.messages DROP CONSTRAINT IF EXISTS messages_pkey;
ALTER TABLE IF EXISTS ONLY public.product_variants DROP CONSTRAINT IF EXISTS variant_unique_combination;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_pkey;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_email_key;
ALTER TABLE IF EXISTS ONLY public.user_roles DROP CONSTRAINT IF EXISTS user_roles_pkey;
ALTER TABLE IF EXISTS ONLY public.user_permissions DROP CONSTRAINT IF EXISTS user_permissions_pkey;
ALTER TABLE IF EXISTS ONLY public.user_addresses DROP CONSTRAINT IF EXISTS user_addresses_pkey;
ALTER TABLE IF EXISTS ONLY public.favorites DROP CONSTRAINT IF EXISTS unique_user_product;
ALTER TABLE IF EXISTS ONLY public.cart_items DROP CONSTRAINT IF EXISTS unique_cart_item;
ALTER TABLE IF EXISTS ONLY public.tenants DROP CONSTRAINT IF EXISTS tenants_pkey;
ALTER TABLE IF EXISTS ONLY public.system_settings DROP CONSTRAINT IF EXISTS system_settings_pkey;
ALTER TABLE IF EXISTS ONLY public.shipping_providers DROP CONSTRAINT IF EXISTS shipping_providers_pkey;
ALTER TABLE IF EXISTS ONLY public.shipping_configs DROP CONSTRAINT IF EXISTS shipping_configs_pkey;
ALTER TABLE IF EXISTS ONLY public.shipments DROP CONSTRAINT IF EXISTS shipments_pkey;
ALTER TABLE IF EXISTS ONLY public.shipment_events DROP CONSTRAINT IF EXISTS shipment_events_pkey;
ALTER TABLE IF EXISTS ONLY public.roles DROP CONSTRAINT IF EXISTS roles_pkey;
ALTER TABLE IF EXISTS ONLY public.role_permissions DROP CONSTRAINT IF EXISTS role_permissions_pkey;
ALTER TABLE IF EXISTS ONLY public.return_requests DROP CONSTRAINT IF EXISTS return_requests_pkey;
ALTER TABLE IF EXISTS ONLY public.products DROP CONSTRAINT IF EXISTS products_pkey;
ALTER TABLE IF EXISTS ONLY public.product_variants DROP CONSTRAINT IF EXISTS product_variants_sku_key;
ALTER TABLE IF EXISTS ONLY public.product_variants DROP CONSTRAINT IF EXISTS product_variants_pkey;
ALTER TABLE IF EXISTS ONLY public.product_reviews DROP CONSTRAINT IF EXISTS product_reviews_pkey;
ALTER TABLE IF EXISTS ONLY public.product_images DROP CONSTRAINT IF EXISTS product_images_pkey;
ALTER TABLE IF EXISTS ONLY public.product_analytics DROP CONSTRAINT IF EXISTS product_analytics_pkey;
ALTER TABLE IF EXISTS ONLY public.product_analytics DROP CONSTRAINT IF EXISTS product_analytics_master_key;
ALTER TABLE IF EXISTS ONLY public.permissions DROP CONSTRAINT IF EXISTS permissions_pkey;
ALTER TABLE IF EXISTS ONLY public.permissions DROP CONSTRAINT IF EXISTS permissions_code_key;
ALTER TABLE IF EXISTS ONLY public.permission_groups DROP CONSTRAINT IF EXISTS permission_groups_pkey;
ALTER TABLE IF EXISTS ONLY public.payments DROP CONSTRAINT IF EXISTS payments_pkey;
ALTER TABLE IF EXISTS ONLY public.orders DROP CONSTRAINT IF EXISTS orders_pkey;
ALTER TABLE IF EXISTS ONLY public.order_items DROP CONSTRAINT IF EXISTS order_items_pkey;
ALTER TABLE IF EXISTS ONLY public.inventory_logs DROP CONSTRAINT IF EXISTS inventory_logs_pkey;
ALTER TABLE IF EXISTS ONLY public.flash_sales DROP CONSTRAINT IF EXISTS flash_sales_pkey;
ALTER TABLE IF EXISTS ONLY public.flash_sale_items DROP CONSTRAINT IF EXISTS flash_sale_items_pkey;
ALTER TABLE IF EXISTS ONLY public.favorites DROP CONSTRAINT IF EXISTS favorites_pkey;
ALTER TABLE IF EXISTS ONLY public.coupons DROP CONSTRAINT IF EXISTS coupons_pkey;
ALTER TABLE IF EXISTS ONLY public.coupons DROP CONSTRAINT IF EXISTS coupons_code_key;
ALTER TABLE IF EXISTS ONLY public.coupon_usages DROP CONSTRAINT IF EXISTS coupon_usages_pkey;
ALTER TABLE IF EXISTS ONLY public.coupon_usages DROP CONSTRAINT IF EXISTS coupon_usages_coupon_id_order_id_key;
ALTER TABLE IF EXISTS ONLY public.coupon_segments DROP CONSTRAINT IF EXISTS coupon_segments_pkey;
ALTER TABLE IF EXISTS ONLY public.coupon_products DROP CONSTRAINT IF EXISTS coupon_products_pkey;
ALTER TABLE IF EXISTS ONLY public.coupon_categories DROP CONSTRAINT IF EXISTS coupon_categories_pkey;
ALTER TABLE IF EXISTS ONLY public.categories DROP CONSTRAINT IF EXISTS categories_slug_key;
ALTER TABLE IF EXISTS ONLY public.categories DROP CONSTRAINT IF EXISTS categories_pkey;
ALTER TABLE IF EXISTS ONLY public.cart_items DROP CONSTRAINT IF EXISTS cart_items_pkey;
ALTER TABLE IF EXISTS ONLY public.carrier_status_mapping DROP CONSTRAINT IF EXISTS carrier_status_mapping_provider_carrier_status_key;
ALTER TABLE IF EXISTS ONLY public.carrier_status_mapping DROP CONSTRAINT IF EXISTS carrier_status_mapping_pkey;
ALTER TABLE IF EXISTS ONLY public.brands DROP CONSTRAINT IF EXISTS brands_slug_key;
ALTER TABLE IF EXISTS ONLY public.brands DROP CONSTRAINT IF EXISTS brands_pkey;
ALTER TABLE IF EXISTS ONLY public.audit_logs DROP CONSTRAINT IF EXISTS audit_logs_pkey;
ALTER TABLE IF EXISTS ONLY auth.webauthn_credentials DROP CONSTRAINT IF EXISTS webauthn_credentials_pkey;
ALTER TABLE IF EXISTS ONLY auth.webauthn_challenges DROP CONSTRAINT IF EXISTS webauthn_challenges_pkey;
ALTER TABLE IF EXISTS ONLY auth.users DROP CONSTRAINT IF EXISTS users_pkey;
ALTER TABLE IF EXISTS ONLY auth.users DROP CONSTRAINT IF EXISTS users_phone_key;
ALTER TABLE IF EXISTS ONLY auth.sso_providers DROP CONSTRAINT IF EXISTS sso_providers_pkey;
ALTER TABLE IF EXISTS ONLY auth.sso_domains DROP CONSTRAINT IF EXISTS sso_domains_pkey;
ALTER TABLE IF EXISTS ONLY auth.sessions DROP CONSTRAINT IF EXISTS sessions_pkey;
ALTER TABLE IF EXISTS ONLY auth.schema_migrations DROP CONSTRAINT IF EXISTS schema_migrations_pkey;
ALTER TABLE IF EXISTS ONLY auth.saml_relay_states DROP CONSTRAINT IF EXISTS saml_relay_states_pkey;
ALTER TABLE IF EXISTS ONLY auth.saml_providers DROP CONSTRAINT IF EXISTS saml_providers_pkey;
ALTER TABLE IF EXISTS ONLY auth.saml_providers DROP CONSTRAINT IF EXISTS saml_providers_entity_id_key;
ALTER TABLE IF EXISTS ONLY auth.refresh_tokens DROP CONSTRAINT IF EXISTS refresh_tokens_token_unique;
ALTER TABLE IF EXISTS ONLY auth.refresh_tokens DROP CONSTRAINT IF EXISTS refresh_tokens_pkey;
ALTER TABLE IF EXISTS ONLY auth.one_time_tokens DROP CONSTRAINT IF EXISTS one_time_tokens_pkey;
ALTER TABLE IF EXISTS ONLY auth.oauth_consents DROP CONSTRAINT IF EXISTS oauth_consents_user_client_unique;
ALTER TABLE IF EXISTS ONLY auth.oauth_consents DROP CONSTRAINT IF EXISTS oauth_consents_pkey;
ALTER TABLE IF EXISTS ONLY auth.oauth_clients DROP CONSTRAINT IF EXISTS oauth_clients_pkey;
ALTER TABLE IF EXISTS ONLY auth.oauth_client_states DROP CONSTRAINT IF EXISTS oauth_client_states_pkey;
ALTER TABLE IF EXISTS ONLY auth.oauth_authorizations DROP CONSTRAINT IF EXISTS oauth_authorizations_pkey;
ALTER TABLE IF EXISTS ONLY auth.oauth_authorizations DROP CONSTRAINT IF EXISTS oauth_authorizations_authorization_id_key;
ALTER TABLE IF EXISTS ONLY auth.oauth_authorizations DROP CONSTRAINT IF EXISTS oauth_authorizations_authorization_code_key;
ALTER TABLE IF EXISTS ONLY auth.mfa_factors DROP CONSTRAINT IF EXISTS mfa_factors_pkey;
ALTER TABLE IF EXISTS ONLY auth.mfa_factors DROP CONSTRAINT IF EXISTS mfa_factors_last_challenged_at_key;
ALTER TABLE IF EXISTS ONLY auth.mfa_challenges DROP CONSTRAINT IF EXISTS mfa_challenges_pkey;
ALTER TABLE IF EXISTS ONLY auth.mfa_amr_claims DROP CONSTRAINT IF EXISTS mfa_amr_claims_session_id_authentication_method_pkey;
ALTER TABLE IF EXISTS ONLY auth.instances DROP CONSTRAINT IF EXISTS instances_pkey;
ALTER TABLE IF EXISTS ONLY auth.identities DROP CONSTRAINT IF EXISTS identities_provider_id_provider_unique;
ALTER TABLE IF EXISTS ONLY auth.identities DROP CONSTRAINT IF EXISTS identities_pkey;
ALTER TABLE IF EXISTS ONLY auth.flow_state DROP CONSTRAINT IF EXISTS flow_state_pkey;
ALTER TABLE IF EXISTS ONLY auth.custom_oauth_providers DROP CONSTRAINT IF EXISTS custom_oauth_providers_pkey;
ALTER TABLE IF EXISTS ONLY auth.custom_oauth_providers DROP CONSTRAINT IF EXISTS custom_oauth_providers_identifier_key;
ALTER TABLE IF EXISTS ONLY auth.audit_log_entries DROP CONSTRAINT IF EXISTS audit_log_entries_pkey;
ALTER TABLE IF EXISTS ONLY auth.mfa_amr_claims DROP CONSTRAINT IF EXISTS amr_id_pk;
ALTER TABLE IF EXISTS public.roles ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.permissions ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.permission_groups ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.carrier_status_mapping ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS auth.refresh_tokens ALTER COLUMN id DROP DEFAULT;
DROP TABLE IF EXISTS storage.vector_indexes;
DROP TABLE IF EXISTS storage.s3_multipart_uploads_parts;
DROP TABLE IF EXISTS storage.s3_multipart_uploads;
DROP TABLE IF EXISTS storage.objects;
DROP TABLE IF EXISTS storage.migrations;
DROP TABLE IF EXISTS storage.buckets_vectors;
DROP TABLE IF EXISTS storage.buckets_analytics;
DROP TABLE IF EXISTS storage.buckets;
DROP TABLE IF EXISTS realtime.subscription;
DROP TABLE IF EXISTS realtime.schema_migrations;
DROP TABLE IF EXISTS realtime.messages;
DROP TABLE IF EXISTS public.webhook_logs;
DROP TABLE IF EXISTS public.users;
DROP TABLE IF EXISTS public.user_roles;
DROP TABLE IF EXISTS public.user_permissions;
DROP TABLE IF EXISTS public.user_addresses;
DROP TABLE IF EXISTS public.tenants;
DROP TABLE IF EXISTS public.system_settings;
DROP TABLE IF EXISTS public.shipping_providers;
DROP TABLE IF EXISTS public.shipping_configs;
DROP TABLE IF EXISTS public.shipments;
DROP TABLE IF EXISTS public.shipment_events;
DROP SEQUENCE IF EXISTS public.roles_id_seq;
DROP TABLE IF EXISTS public.roles;
DROP TABLE IF EXISTS public.role_permissions;
DROP TABLE IF EXISTS public.return_requests;
DROP TABLE IF EXISTS public.products;
DROP TABLE IF EXISTS public.product_variants;
DROP TABLE IF EXISTS public.product_reviews;
DROP TABLE IF EXISTS public.product_images;
DROP TABLE IF EXISTS public.product_analytics;
DROP SEQUENCE IF EXISTS public.permissions_id_seq;
DROP TABLE IF EXISTS public.permissions;
DROP SEQUENCE IF EXISTS public.permission_groups_id_seq;
DROP TABLE IF EXISTS public.permission_groups;
DROP TABLE IF EXISTS public.payments;
DROP TABLE IF EXISTS public.orders;
DROP TABLE IF EXISTS public.order_items;
DROP TABLE IF EXISTS public.inventory_logs;
DROP TABLE IF EXISTS public.flash_sales;
DROP TABLE IF EXISTS public.flash_sale_items;
DROP TABLE IF EXISTS public.favorites;
DROP TABLE IF EXISTS public.coupons;
DROP TABLE IF EXISTS public.coupon_usages;
DROP TABLE IF EXISTS public.coupon_segments;
DROP TABLE IF EXISTS public.coupon_products;
DROP TABLE IF EXISTS public.coupon_categories;
DROP TABLE IF EXISTS public.categories;
DROP TABLE IF EXISTS public.cart_items;
DROP SEQUENCE IF EXISTS public.carrier_status_mapping_id_seq;
DROP TABLE IF EXISTS public.carrier_status_mapping;
DROP TABLE IF EXISTS public.brands;
DROP TABLE IF EXISTS public.audit_logs;
DROP TABLE IF EXISTS auth.webauthn_credentials;
DROP TABLE IF EXISTS auth.webauthn_challenges;
DROP TABLE IF EXISTS auth.users;
DROP TABLE IF EXISTS auth.sso_providers;
DROP TABLE IF EXISTS auth.sso_domains;
DROP TABLE IF EXISTS auth.sessions;
DROP TABLE IF EXISTS auth.schema_migrations;
DROP TABLE IF EXISTS auth.saml_relay_states;
DROP TABLE IF EXISTS auth.saml_providers;
DROP SEQUENCE IF EXISTS auth.refresh_tokens_id_seq;
DROP TABLE IF EXISTS auth.refresh_tokens;
DROP TABLE IF EXISTS auth.one_time_tokens;
DROP TABLE IF EXISTS auth.oauth_consents;
DROP TABLE IF EXISTS auth.oauth_clients;
DROP TABLE IF EXISTS auth.oauth_client_states;
DROP TABLE IF EXISTS auth.oauth_authorizations;
DROP TABLE IF EXISTS auth.mfa_factors;
DROP TABLE IF EXISTS auth.mfa_challenges;
DROP TABLE IF EXISTS auth.mfa_amr_claims;
DROP TABLE IF EXISTS auth.instances;
DROP TABLE IF EXISTS auth.identities;
DROP TABLE IF EXISTS auth.flow_state;
DROP TABLE IF EXISTS auth.custom_oauth_providers;
DROP TABLE IF EXISTS auth.audit_log_entries;
DROP FUNCTION IF EXISTS storage.update_updated_at_column();
DROP FUNCTION IF EXISTS storage.search_v2(prefix text, bucket_name text, limits integer, levels integer, start_after text, sort_order text, sort_column text, sort_column_after text);
DROP FUNCTION IF EXISTS storage.search_by_timestamp(p_prefix text, p_bucket_id text, p_limit integer, p_level integer, p_start_after text, p_sort_order text, p_sort_column text, p_sort_column_after text);
DROP FUNCTION IF EXISTS storage.search(prefix text, bucketname text, limits integer, levels integer, offsets integer, search text, sortcolumn text, sortorder text);
DROP FUNCTION IF EXISTS storage.protect_delete();
DROP FUNCTION IF EXISTS storage.operation();
DROP FUNCTION IF EXISTS storage.list_objects_with_delimiter(_bucket_id text, prefix_param text, delimiter_param text, max_keys integer, start_after text, next_token text, sort_order text);
DROP FUNCTION IF EXISTS storage.list_multipart_uploads_with_delimiter(bucket_id text, prefix_param text, delimiter_param text, max_keys integer, next_key_token text, next_upload_token text);
DROP FUNCTION IF EXISTS storage.get_size_by_bucket();
DROP FUNCTION IF EXISTS storage.get_common_prefix(p_key text, p_prefix text, p_delimiter text);
DROP FUNCTION IF EXISTS storage.foldername(name text);
DROP FUNCTION IF EXISTS storage.filename(name text);
DROP FUNCTION IF EXISTS storage.extension(name text);
DROP FUNCTION IF EXISTS storage.enforce_bucket_name_length();
DROP FUNCTION IF EXISTS storage.can_insert_object(bucketid text, name text, owner uuid, metadata jsonb);
DROP FUNCTION IF EXISTS storage.allow_only_operation(expected_operation text);
DROP FUNCTION IF EXISTS storage.allow_any_operation(expected_operations text[]);
DROP FUNCTION IF EXISTS realtime.topic();
DROP FUNCTION IF EXISTS realtime.to_regrole(role_name text);
DROP FUNCTION IF EXISTS realtime.subscription_check_filters();
DROP FUNCTION IF EXISTS realtime.send(payload jsonb, event text, topic text, private boolean);
DROP FUNCTION IF EXISTS realtime.quote_wal2json(entity regclass);
DROP FUNCTION IF EXISTS realtime.list_changes(publication name, slot_name name, max_changes integer, max_record_bytes integer);
DROP FUNCTION IF EXISTS realtime.is_visible_through_filters(columns realtime.wal_column[], filters realtime.user_defined_filter[]);
DROP FUNCTION IF EXISTS realtime.check_equality_op(op realtime.equality_op, type_ regtype, val_1 text, val_2 text);
DROP FUNCTION IF EXISTS realtime."cast"(val text, type_ regtype);
DROP FUNCTION IF EXISTS realtime.build_prepared_statement_sql(prepared_statement_name text, entity regclass, columns realtime.wal_column[]);
DROP FUNCTION IF EXISTS realtime.broadcast_changes(topic_name text, event_name text, operation text, table_name text, table_schema text, new record, old record, level text);
DROP FUNCTION IF EXISTS realtime.apply_rls(wal jsonb, max_record_bytes integer);
DROP FUNCTION IF EXISTS public.update_updated_at_column();
DROP FUNCTION IF EXISTS public.update_modified_column();
DROP FUNCTION IF EXISTS public.rls_auto_enable();
DROP FUNCTION IF EXISTS public.log_product_event(p_product_id uuid, p_channel text, p_source text, p_event_type text, p_revenue numeric, p_qty integer);
DROP FUNCTION IF EXISTS public.is_user_in_segment(p_user_id uuid, p_segment text);
DROP FUNCTION IF EXISTS public.get_product_count_by_category();
DROP FUNCTION IF EXISTS public.get_cart_total_quantity(p_user_id uuid);
DROP FUNCTION IF EXISTS public.apply_coupon(p_code text, p_user_id uuid, p_order_id uuid);
DROP FUNCTION IF EXISTS public.add_item_to_cart(p_user_id uuid, p_product_id uuid, p_quantity integer, p_size text);
DROP FUNCTION IF EXISTS pgbouncer.get_auth(p_usename text);
DROP FUNCTION IF EXISTS graphql_public.graphql("operationName" text, query text, variables jsonb, extensions jsonb);
DROP FUNCTION IF EXISTS extensions.set_graphql_placeholder();
DROP FUNCTION IF EXISTS extensions.pgrst_drop_watch();
DROP FUNCTION IF EXISTS extensions.pgrst_ddl_watch();
DROP FUNCTION IF EXISTS extensions.grant_pg_net_access();
DROP FUNCTION IF EXISTS extensions.grant_pg_graphql_access();
DROP FUNCTION IF EXISTS extensions.grant_pg_cron_access();
DROP FUNCTION IF EXISTS auth.uid();
DROP FUNCTION IF EXISTS auth.role();
DROP FUNCTION IF EXISTS auth.jwt();
DROP FUNCTION IF EXISTS auth.email();
DROP TYPE IF EXISTS storage.buckettype;
DROP TYPE IF EXISTS realtime.wal_rls;
DROP TYPE IF EXISTS realtime.wal_column;
DROP TYPE IF EXISTS realtime.user_defined_filter;
DROP TYPE IF EXISTS realtime.equality_op;
DROP TYPE IF EXISTS realtime.action;
DROP TYPE IF EXISTS public.shipment_status;
DROP TYPE IF EXISTS auth.one_time_token_type;
DROP TYPE IF EXISTS auth.oauth_response_type;
DROP TYPE IF EXISTS auth.oauth_registration_type;
DROP TYPE IF EXISTS auth.oauth_client_type;
DROP TYPE IF EXISTS auth.oauth_authorization_status;
DROP TYPE IF EXISTS auth.factor_type;
DROP TYPE IF EXISTS auth.factor_status;
DROP TYPE IF EXISTS auth.code_challenge_method;
DROP TYPE IF EXISTS auth.aal_level;
DROP EXTENSION IF EXISTS "uuid-ossp";
DROP EXTENSION IF EXISTS supabase_vault;
DROP EXTENSION IF EXISTS pgcrypto;
DROP EXTENSION IF EXISTS pg_stat_statements;
DROP SCHEMA IF EXISTS vault;
DROP SCHEMA IF EXISTS storage;
DROP SCHEMA IF EXISTS realtime;
DROP SCHEMA IF EXISTS pgbouncer;
DROP SCHEMA IF EXISTS graphql_public;
DROP SCHEMA IF EXISTS graphql;
DROP SCHEMA IF EXISTS extensions;
DROP SCHEMA IF EXISTS auth;
--
-- Name: auth; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA auth;


--
-- Name: extensions; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA extensions;


--
-- Name: graphql; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA graphql;


--
-- Name: graphql_public; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA graphql_public;


--
-- Name: pgbouncer; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA pgbouncer;


--
-- Name: realtime; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA realtime;


--
-- Name: storage; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA storage;


--
-- Name: vault; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA vault;


--
-- Name: pg_stat_statements; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_stat_statements WITH SCHEMA extensions;


--
-- Name: EXTENSION pg_stat_statements; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pg_stat_statements IS 'track planning and execution statistics of all SQL statements executed';


--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA extensions;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- Name: supabase_vault; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS supabase_vault WITH SCHEMA vault;


--
-- Name: EXTENSION supabase_vault; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION supabase_vault IS 'Supabase Vault Extension';


--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA extensions;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: aal_level; Type: TYPE; Schema: auth; Owner: -
--

CREATE TYPE auth.aal_level AS ENUM (
    'aal1',
    'aal2',
    'aal3'
);


--
-- Name: code_challenge_method; Type: TYPE; Schema: auth; Owner: -
--

CREATE TYPE auth.code_challenge_method AS ENUM (
    's256',
    'plain'
);


--
-- Name: factor_status; Type: TYPE; Schema: auth; Owner: -
--

CREATE TYPE auth.factor_status AS ENUM (
    'unverified',
    'verified'
);


--
-- Name: factor_type; Type: TYPE; Schema: auth; Owner: -
--

CREATE TYPE auth.factor_type AS ENUM (
    'totp',
    'webauthn',
    'phone'
);


--
-- Name: oauth_authorization_status; Type: TYPE; Schema: auth; Owner: -
--

CREATE TYPE auth.oauth_authorization_status AS ENUM (
    'pending',
    'approved',
    'denied',
    'expired'
);


--
-- Name: oauth_client_type; Type: TYPE; Schema: auth; Owner: -
--

CREATE TYPE auth.oauth_client_type AS ENUM (
    'public',
    'confidential'
);


--
-- Name: oauth_registration_type; Type: TYPE; Schema: auth; Owner: -
--

CREATE TYPE auth.oauth_registration_type AS ENUM (
    'dynamic',
    'manual'
);


--
-- Name: oauth_response_type; Type: TYPE; Schema: auth; Owner: -
--

CREATE TYPE auth.oauth_response_type AS ENUM (
    'code'
);


--
-- Name: one_time_token_type; Type: TYPE; Schema: auth; Owner: -
--

CREATE TYPE auth.one_time_token_type AS ENUM (
    'confirmation_token',
    'reauthentication_token',
    'recovery_token',
    'email_change_token_new',
    'email_change_token_current',
    'phone_change_token'
);


--
-- Name: shipment_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.shipment_status AS ENUM (
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


--
-- Name: action; Type: TYPE; Schema: realtime; Owner: -
--

CREATE TYPE realtime.action AS ENUM (
    'INSERT',
    'UPDATE',
    'DELETE',
    'TRUNCATE',
    'ERROR'
);


--
-- Name: equality_op; Type: TYPE; Schema: realtime; Owner: -
--

CREATE TYPE realtime.equality_op AS ENUM (
    'eq',
    'neq',
    'lt',
    'lte',
    'gt',
    'gte',
    'in'
);


--
-- Name: user_defined_filter; Type: TYPE; Schema: realtime; Owner: -
--

CREATE TYPE realtime.user_defined_filter AS (
	column_name text,
	op realtime.equality_op,
	value text
);


--
-- Name: wal_column; Type: TYPE; Schema: realtime; Owner: -
--

CREATE TYPE realtime.wal_column AS (
	name text,
	type_name text,
	type_oid oid,
	value jsonb,
	is_pkey boolean,
	is_selectable boolean
);


--
-- Name: wal_rls; Type: TYPE; Schema: realtime; Owner: -
--

CREATE TYPE realtime.wal_rls AS (
	wal jsonb,
	is_rls_enabled boolean,
	subscription_ids uuid[],
	errors text[]
);


--
-- Name: buckettype; Type: TYPE; Schema: storage; Owner: -
--

CREATE TYPE storage.buckettype AS ENUM (
    'STANDARD',
    'ANALYTICS',
    'VECTOR'
);


--
-- Name: email(); Type: FUNCTION; Schema: auth; Owner: -
--

CREATE FUNCTION auth.email() RETURNS text
    LANGUAGE sql STABLE
    AS $$
  select 
  coalesce(
    nullif(current_setting('request.jwt.claim.email', true), ''),
    (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'email')
  )::text
$$;


--
-- Name: FUNCTION email(); Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON FUNCTION auth.email() IS 'Deprecated. Use auth.jwt() -> ''email'' instead.';


--
-- Name: jwt(); Type: FUNCTION; Schema: auth; Owner: -
--

CREATE FUNCTION auth.jwt() RETURNS jsonb
    LANGUAGE sql STABLE
    AS $$
  select 
    coalesce(
        nullif(current_setting('request.jwt.claim', true), ''),
        nullif(current_setting('request.jwt.claims', true), '')
    )::jsonb
$$;


--
-- Name: role(); Type: FUNCTION; Schema: auth; Owner: -
--

CREATE FUNCTION auth.role() RETURNS text
    LANGUAGE sql STABLE
    AS $$
  select 
  coalesce(
    nullif(current_setting('request.jwt.claim.role', true), ''),
    (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'role')
  )::text
$$;


--
-- Name: FUNCTION role(); Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON FUNCTION auth.role() IS 'Deprecated. Use auth.jwt() -> ''role'' instead.';


--
-- Name: uid(); Type: FUNCTION; Schema: auth; Owner: -
--

CREATE FUNCTION auth.uid() RETURNS uuid
    LANGUAGE sql STABLE
    AS $$
  select 
  coalesce(
    nullif(current_setting('request.jwt.claim.sub', true), ''),
    (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub')
  )::uuid
$$;


--
-- Name: FUNCTION uid(); Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON FUNCTION auth.uid() IS 'Deprecated. Use auth.jwt() -> ''sub'' instead.';


--
-- Name: grant_pg_cron_access(); Type: FUNCTION; Schema: extensions; Owner: -
--

CREATE FUNCTION extensions.grant_pg_cron_access() RETURNS event_trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  IF EXISTS (
    SELECT
    FROM pg_event_trigger_ddl_commands() AS ev
    JOIN pg_extension AS ext
    ON ev.objid = ext.oid
    WHERE ext.extname = 'pg_cron'
  )
  THEN
    grant usage on schema cron to postgres with grant option;

    alter default privileges in schema cron grant all on tables to postgres with grant option;
    alter default privileges in schema cron grant all on functions to postgres with grant option;
    alter default privileges in schema cron grant all on sequences to postgres with grant option;

    alter default privileges for user supabase_admin in schema cron grant all
        on sequences to postgres with grant option;
    alter default privileges for user supabase_admin in schema cron grant all
        on tables to postgres with grant option;
    alter default privileges for user supabase_admin in schema cron grant all
        on functions to postgres with grant option;

    grant all privileges on all tables in schema cron to postgres with grant option;
    revoke all on table cron.job from postgres;
    grant select on table cron.job to postgres with grant option;
  END IF;
END;
$$;


--
-- Name: FUNCTION grant_pg_cron_access(); Type: COMMENT; Schema: extensions; Owner: -
--

COMMENT ON FUNCTION extensions.grant_pg_cron_access() IS 'Grants access to pg_cron';


--
-- Name: grant_pg_graphql_access(); Type: FUNCTION; Schema: extensions; Owner: -
--

CREATE FUNCTION extensions.grant_pg_graphql_access() RETURNS event_trigger
    LANGUAGE plpgsql
    AS $_$
DECLARE
    func_is_graphql_resolve bool;
BEGIN
    func_is_graphql_resolve = (
        SELECT n.proname = 'resolve'
        FROM pg_event_trigger_ddl_commands() AS ev
        LEFT JOIN pg_catalog.pg_proc AS n
        ON ev.objid = n.oid
    );

    IF func_is_graphql_resolve
    THEN
        -- Update public wrapper to pass all arguments through to the pg_graphql resolve func
        DROP FUNCTION IF EXISTS graphql_public.graphql;
        create or replace function graphql_public.graphql(
            "operationName" text default null,
            query text default null,
            variables jsonb default null,
            extensions jsonb default null
        )
            returns jsonb
            language sql
        as $$
            select graphql.resolve(
                query := query,
                variables := coalesce(variables, '{}'),
                "operationName" := "operationName",
                extensions := extensions
            );
        $$;

        -- This hook executes when `graphql.resolve` is created. That is not necessarily the last
        -- function in the extension so we need to grant permissions on existing entities AND
        -- update default permissions to any others that are created after `graphql.resolve`
        grant usage on schema graphql to postgres, anon, authenticated, service_role;
        grant select on all tables in schema graphql to postgres, anon, authenticated, service_role;
        grant execute on all functions in schema graphql to postgres, anon, authenticated, service_role;
        grant all on all sequences in schema graphql to postgres, anon, authenticated, service_role;
        alter default privileges in schema graphql grant all on tables to postgres, anon, authenticated, service_role;
        alter default privileges in schema graphql grant all on functions to postgres, anon, authenticated, service_role;
        alter default privileges in schema graphql grant all on sequences to postgres, anon, authenticated, service_role;

        -- Allow postgres role to allow granting usage on graphql and graphql_public schemas to custom roles
        grant usage on schema graphql_public to postgres with grant option;
        grant usage on schema graphql to postgres with grant option;
    END IF;

END;
$_$;


--
-- Name: FUNCTION grant_pg_graphql_access(); Type: COMMENT; Schema: extensions; Owner: -
--

COMMENT ON FUNCTION extensions.grant_pg_graphql_access() IS 'Grants access to pg_graphql';


--
-- Name: grant_pg_net_access(); Type: FUNCTION; Schema: extensions; Owner: -
--

CREATE FUNCTION extensions.grant_pg_net_access() RETURNS event_trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM pg_event_trigger_ddl_commands() AS ev
    JOIN pg_extension AS ext
    ON ev.objid = ext.oid
    WHERE ext.extname = 'pg_net'
  )
  THEN
    IF NOT EXISTS (
      SELECT 1
      FROM pg_roles
      WHERE rolname = 'supabase_functions_admin'
    )
    THEN
      CREATE USER supabase_functions_admin NOINHERIT CREATEROLE LOGIN NOREPLICATION;
    END IF;

    GRANT USAGE ON SCHEMA net TO supabase_functions_admin, postgres, anon, authenticated, service_role;

    IF EXISTS (
      SELECT FROM pg_extension
      WHERE extname = 'pg_net'
      -- all versions in use on existing projects as of 2025-02-20
      -- version 0.12.0 onwards don't need these applied
      AND extversion IN ('0.2', '0.6', '0.7', '0.7.1', '0.8', '0.10.0', '0.11.0')
    ) THEN
      ALTER function net.http_get(url text, params jsonb, headers jsonb, timeout_milliseconds integer) SECURITY DEFINER;
      ALTER function net.http_post(url text, body jsonb, params jsonb, headers jsonb, timeout_milliseconds integer) SECURITY DEFINER;

      ALTER function net.http_get(url text, params jsonb, headers jsonb, timeout_milliseconds integer) SET search_path = net;
      ALTER function net.http_post(url text, body jsonb, params jsonb, headers jsonb, timeout_milliseconds integer) SET search_path = net;

      REVOKE ALL ON FUNCTION net.http_get(url text, params jsonb, headers jsonb, timeout_milliseconds integer) FROM PUBLIC;
      REVOKE ALL ON FUNCTION net.http_post(url text, body jsonb, params jsonb, headers jsonb, timeout_milliseconds integer) FROM PUBLIC;

      GRANT EXECUTE ON FUNCTION net.http_get(url text, params jsonb, headers jsonb, timeout_milliseconds integer) TO supabase_functions_admin, postgres, anon, authenticated, service_role;
      GRANT EXECUTE ON FUNCTION net.http_post(url text, body jsonb, params jsonb, headers jsonb, timeout_milliseconds integer) TO supabase_functions_admin, postgres, anon, authenticated, service_role;
    END IF;
  END IF;
END;
$$;


--
-- Name: FUNCTION grant_pg_net_access(); Type: COMMENT; Schema: extensions; Owner: -
--

COMMENT ON FUNCTION extensions.grant_pg_net_access() IS 'Grants access to pg_net';


--
-- Name: pgrst_ddl_watch(); Type: FUNCTION; Schema: extensions; Owner: -
--

CREATE FUNCTION extensions.pgrst_ddl_watch() RETURNS event_trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
  cmd record;
BEGIN
  FOR cmd IN SELECT * FROM pg_event_trigger_ddl_commands()
  LOOP
    IF cmd.command_tag IN (
      'CREATE SCHEMA', 'ALTER SCHEMA'
    , 'CREATE TABLE', 'CREATE TABLE AS', 'SELECT INTO', 'ALTER TABLE'
    , 'CREATE FOREIGN TABLE', 'ALTER FOREIGN TABLE'
    , 'CREATE VIEW', 'ALTER VIEW'
    , 'CREATE MATERIALIZED VIEW', 'ALTER MATERIALIZED VIEW'
    , 'CREATE FUNCTION', 'ALTER FUNCTION'
    , 'CREATE TRIGGER'
    , 'CREATE TYPE', 'ALTER TYPE'
    , 'CREATE RULE'
    , 'COMMENT'
    )
    -- don't notify in case of CREATE TEMP table or other objects created on pg_temp
    AND cmd.schema_name is distinct from 'pg_temp'
    THEN
      NOTIFY pgrst, 'reload schema';
    END IF;
  END LOOP;
END; $$;


--
-- Name: pgrst_drop_watch(); Type: FUNCTION; Schema: extensions; Owner: -
--

CREATE FUNCTION extensions.pgrst_drop_watch() RETURNS event_trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
  obj record;
BEGIN
  FOR obj IN SELECT * FROM pg_event_trigger_dropped_objects()
  LOOP
    IF obj.object_type IN (
      'schema'
    , 'table'
    , 'foreign table'
    , 'view'
    , 'materialized view'
    , 'function'
    , 'trigger'
    , 'type'
    , 'rule'
    )
    AND obj.is_temporary IS false -- no pg_temp objects
    THEN
      NOTIFY pgrst, 'reload schema';
    END IF;
  END LOOP;
END; $$;


--
-- Name: set_graphql_placeholder(); Type: FUNCTION; Schema: extensions; Owner: -
--

CREATE FUNCTION extensions.set_graphql_placeholder() RETURNS event_trigger
    LANGUAGE plpgsql
    AS $_$
    DECLARE
    graphql_is_dropped bool;
    BEGIN
    graphql_is_dropped = (
        SELECT ev.schema_name = 'graphql_public'
        FROM pg_event_trigger_dropped_objects() AS ev
        WHERE ev.schema_name = 'graphql_public'
    );

    IF graphql_is_dropped
    THEN
        create or replace function graphql_public.graphql(
            "operationName" text default null,
            query text default null,
            variables jsonb default null,
            extensions jsonb default null
        )
            returns jsonb
            language plpgsql
        as $$
            DECLARE
                server_version float;
            BEGIN
                server_version = (SELECT (SPLIT_PART((select version()), ' ', 2))::float);

                IF server_version >= 14 THEN
                    RETURN jsonb_build_object(
                        'errors', jsonb_build_array(
                            jsonb_build_object(
                                'message', 'pg_graphql extension is not enabled.'
                            )
                        )
                    );
                ELSE
                    RETURN jsonb_build_object(
                        'errors', jsonb_build_array(
                            jsonb_build_object(
                                'message', 'pg_graphql is only available on projects running Postgres 14 onwards.'
                            )
                        )
                    );
                END IF;
            END;
        $$;
    END IF;

    END;
$_$;


--
-- Name: FUNCTION set_graphql_placeholder(); Type: COMMENT; Schema: extensions; Owner: -
--

COMMENT ON FUNCTION extensions.set_graphql_placeholder() IS 'Reintroduces placeholder function for graphql_public.graphql';


--
-- Name: graphql(text, text, jsonb, jsonb); Type: FUNCTION; Schema: graphql_public; Owner: -
--

CREATE FUNCTION graphql_public.graphql("operationName" text DEFAULT NULL::text, query text DEFAULT NULL::text, variables jsonb DEFAULT NULL::jsonb, extensions jsonb DEFAULT NULL::jsonb) RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
            DECLARE
                server_version float;
            BEGIN
                server_version = (SELECT (SPLIT_PART((select version()), ' ', 2))::float);

                IF server_version >= 14 THEN
                    RETURN jsonb_build_object(
                        'errors', jsonb_build_array(
                            jsonb_build_object(
                                'message', 'pg_graphql extension is not enabled.'
                            )
                        )
                    );
                ELSE
                    RETURN jsonb_build_object(
                        'errors', jsonb_build_array(
                            jsonb_build_object(
                                'message', 'pg_graphql is only available on projects running Postgres 14 onwards.'
                            )
                        )
                    );
                END IF;
            END;
        $$;


--
-- Name: get_auth(text); Type: FUNCTION; Schema: pgbouncer; Owner: -
--

CREATE FUNCTION pgbouncer.get_auth(p_usename text) RETURNS TABLE(username text, password text)
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO ''
    AS $_$
  BEGIN
      RAISE DEBUG 'PgBouncer auth request: %', p_usename;

      RETURN QUERY
      SELECT
          rolname::text,
          CASE WHEN rolvaliduntil < now()
              THEN null
              ELSE rolpassword::text
          END
      FROM pg_authid
      WHERE rolname=$1 and rolcanlogin;
  END;
  $_$;


--
-- Name: add_item_to_cart(uuid, uuid, integer, text); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.add_item_to_cart(p_user_id uuid, p_product_id uuid, p_quantity integer, p_size text) RETURNS json
    LANGUAGE plpgsql
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


--
-- Name: apply_coupon(text, uuid, uuid); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.apply_coupon(p_code text, p_user_id uuid, p_order_id uuid) RETURNS jsonb
    LANGUAGE plpgsql
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


--
-- Name: get_cart_total_quantity(uuid); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.get_cart_total_quantity(p_user_id uuid) RETURNS integer
    LANGUAGE plpgsql
    AS $$
BEGIN
  RETURN (
    SELECT COALESCE(SUM(quantity), 0) 
    FROM cart_items 
    WHERE user_id = p_user_id
  );
END;
$$;


--
-- Name: get_product_count_by_category(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.get_product_count_by_category() RETURNS TABLE(name text, count bigint)
    LANGUAGE plpgsql
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


--
-- Name: is_user_in_segment(uuid, text); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.is_user_in_segment(p_user_id uuid, p_segment text) RETURNS boolean
    LANGUAGE plpgsql
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


--
-- Name: log_product_event(uuid, text, text, text, numeric, integer); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.log_product_event(p_product_id uuid, p_channel text, p_source text, p_event_type text, p_revenue numeric DEFAULT 0, p_qty integer DEFAULT 1) RETURNS void
    LANGUAGE plpgsql
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


--
-- Name: rls_auto_enable(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.rls_auto_enable() RETURNS event_trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'pg_catalog'
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


--
-- Name: update_modified_column(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_modified_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;


--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;


--
-- Name: apply_rls(jsonb, integer); Type: FUNCTION; Schema: realtime; Owner: -
--

CREATE FUNCTION realtime.apply_rls(wal jsonb, max_record_bytes integer DEFAULT (1024 * 1024)) RETURNS SETOF realtime.wal_rls
    LANGUAGE plpgsql
    AS $$
declare
-- Regclass of the table e.g. public.notes
entity_ regclass = (quote_ident(wal ->> 'schema') || '.' || quote_ident(wal ->> 'table'))::regclass;

-- I, U, D, T: insert, update ...
action realtime.action = (
    case wal ->> 'action'
        when 'I' then 'INSERT'
        when 'U' then 'UPDATE'
        when 'D' then 'DELETE'
        else 'ERROR'
    end
);

-- Is row level security enabled for the table
is_rls_enabled bool = relrowsecurity from pg_class where oid = entity_;

subscriptions realtime.subscription[] = array_agg(subs)
    from
        realtime.subscription subs
    where
        subs.entity = entity_
        -- Filter by action early - only get subscriptions interested in this action
        -- action_filter column can be: '*' (all), 'INSERT', 'UPDATE', or 'DELETE'
        and (subs.action_filter = '*' or subs.action_filter = action::text);

-- Subscription vars
roles regrole[] = array_agg(distinct us.claims_role::text)
    from
        unnest(subscriptions) us;

working_role regrole;
claimed_role regrole;
claims jsonb;

subscription_id uuid;
subscription_has_access bool;
visible_to_subscription_ids uuid[] = '{}';

-- structured info for wal's columns
columns realtime.wal_column[];
-- previous identity values for update/delete
old_columns realtime.wal_column[];

error_record_exceeds_max_size boolean = octet_length(wal::text) > max_record_bytes;

-- Primary jsonb output for record
output jsonb;

begin
perform set_config('role', null, true);

columns =
    array_agg(
        (
            x->>'name',
            x->>'type',
            x->>'typeoid',
            realtime.cast(
                (x->'value') #>> '{}',
                coalesce(
                    (x->>'typeoid')::regtype, -- null when wal2json version <= 2.4
                    (x->>'type')::regtype
                )
            ),
            (pks ->> 'name') is not null,
            true
        )::realtime.wal_column
    )
    from
        jsonb_array_elements(wal -> 'columns') x
        left join jsonb_array_elements(wal -> 'pk') pks
            on (x ->> 'name') = (pks ->> 'name');

old_columns =
    array_agg(
        (
            x->>'name',
            x->>'type',
            x->>'typeoid',
            realtime.cast(
                (x->'value') #>> '{}',
                coalesce(
                    (x->>'typeoid')::regtype, -- null when wal2json version <= 2.4
                    (x->>'type')::regtype
                )
            ),
            (pks ->> 'name') is not null,
            true
        )::realtime.wal_column
    )
    from
        jsonb_array_elements(wal -> 'identity') x
        left join jsonb_array_elements(wal -> 'pk') pks
            on (x ->> 'name') = (pks ->> 'name');

for working_role in select * from unnest(roles) loop

    -- Update `is_selectable` for columns and old_columns
    columns =
        array_agg(
            (
                c.name,
                c.type_name,
                c.type_oid,
                c.value,
                c.is_pkey,
                pg_catalog.has_column_privilege(working_role, entity_, c.name, 'SELECT')
            )::realtime.wal_column
        )
        from
            unnest(columns) c;

    old_columns =
            array_agg(
                (
                    c.name,
                    c.type_name,
                    c.type_oid,
                    c.value,
                    c.is_pkey,
                    pg_catalog.has_column_privilege(working_role, entity_, c.name, 'SELECT')
                )::realtime.wal_column
            )
            from
                unnest(old_columns) c;

    if action <> 'DELETE' and count(1) = 0 from unnest(columns) c where c.is_pkey then
        return next (
            jsonb_build_object(
                'schema', wal ->> 'schema',
                'table', wal ->> 'table',
                'type', action
            ),
            is_rls_enabled,
            -- subscriptions is already filtered by entity
            (select array_agg(s.subscription_id) from unnest(subscriptions) as s where claims_role = working_role),
            array['Error 400: Bad Request, no primary key']
        )::realtime.wal_rls;

    -- The claims role does not have SELECT permission to the primary key of entity
    elsif action <> 'DELETE' and sum(c.is_selectable::int) <> count(1) from unnest(columns) c where c.is_pkey then
        return next (
            jsonb_build_object(
                'schema', wal ->> 'schema',
                'table', wal ->> 'table',
                'type', action
            ),
            is_rls_enabled,
            (select array_agg(s.subscription_id) from unnest(subscriptions) as s where claims_role = working_role),
            array['Error 401: Unauthorized']
        )::realtime.wal_rls;

    else
        output = jsonb_build_object(
            'schema', wal ->> 'schema',
            'table', wal ->> 'table',
            'type', action,
            'commit_timestamp', to_char(
                ((wal ->> 'timestamp')::timestamptz at time zone 'utc'),
                'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"'
            ),
            'columns', (
                select
                    jsonb_agg(
                        jsonb_build_object(
                            'name', pa.attname,
                            'type', pt.typname
                        )
                        order by pa.attnum asc
                    )
                from
                    pg_attribute pa
                    join pg_type pt
                        on pa.atttypid = pt.oid
                where
                    attrelid = entity_
                    and attnum > 0
                    and pg_catalog.has_column_privilege(working_role, entity_, pa.attname, 'SELECT')
            )
        )
        -- Add "record" key for insert and update
        || case
            when action in ('INSERT', 'UPDATE') then
                jsonb_build_object(
                    'record',
                    (
                        select
                            jsonb_object_agg(
                                -- if unchanged toast, get column name and value from old record
                                coalesce((c).name, (oc).name),
                                case
                                    when (c).name is null then (oc).value
                                    else (c).value
                                end
                            )
                        from
                            unnest(columns) c
                            full outer join unnest(old_columns) oc
                                on (c).name = (oc).name
                        where
                            coalesce((c).is_selectable, (oc).is_selectable)
                            and ( not error_record_exceeds_max_size or (octet_length((c).value::text) <= 64))
                    )
                )
            else '{}'::jsonb
        end
        -- Add "old_record" key for update and delete
        || case
            when action = 'UPDATE' then
                jsonb_build_object(
                        'old_record',
                        (
                            select jsonb_object_agg((c).name, (c).value)
                            from unnest(old_columns) c
                            where
                                (c).is_selectable
                                and ( not error_record_exceeds_max_size or (octet_length((c).value::text) <= 64))
                        )
                    )
            when action = 'DELETE' then
                jsonb_build_object(
                    'old_record',
                    (
                        select jsonb_object_agg((c).name, (c).value)
                        from unnest(old_columns) c
                        where
                            (c).is_selectable
                            and ( not error_record_exceeds_max_size or (octet_length((c).value::text) <= 64))
                            and ( not is_rls_enabled or (c).is_pkey ) -- if RLS enabled, we can't secure deletes so filter to pkey
                    )
                )
            else '{}'::jsonb
        end;

        -- Create the prepared statement
        if is_rls_enabled and action <> 'DELETE' then
            if (select 1 from pg_prepared_statements where name = 'walrus_rls_stmt' limit 1) > 0 then
                deallocate walrus_rls_stmt;
            end if;
            execute realtime.build_prepared_statement_sql('walrus_rls_stmt', entity_, columns);
        end if;

        visible_to_subscription_ids = '{}';

        for subscription_id, claims in (
                select
                    subs.subscription_id,
                    subs.claims
                from
                    unnest(subscriptions) subs
                where
                    subs.entity = entity_
                    and subs.claims_role = working_role
                    and (
                        realtime.is_visible_through_filters(columns, subs.filters)
                        or (
                          action = 'DELETE'
                          and realtime.is_visible_through_filters(old_columns, subs.filters)
                        )
                    )
        ) loop

            if not is_rls_enabled or action = 'DELETE' then
                visible_to_subscription_ids = visible_to_subscription_ids || subscription_id;
            else
                -- Check if RLS allows the role to see the record
                perform
                    -- Trim leading and trailing quotes from working_role because set_config
                    -- doesn't recognize the role as valid if they are included
                    set_config('role', trim(both '"' from working_role::text), true),
                    set_config('request.jwt.claims', claims::text, true);

                execute 'execute walrus_rls_stmt' into subscription_has_access;

                if subscription_has_access then
                    visible_to_subscription_ids = visible_to_subscription_ids || subscription_id;
                end if;
            end if;
        end loop;

        perform set_config('role', null, true);

        return next (
            output,
            is_rls_enabled,
            visible_to_subscription_ids,
            case
                when error_record_exceeds_max_size then array['Error 413: Payload Too Large']
                else '{}'
            end
        )::realtime.wal_rls;

    end if;
end loop;

perform set_config('role', null, true);
end;
$$;


--
-- Name: broadcast_changes(text, text, text, text, text, record, record, text); Type: FUNCTION; Schema: realtime; Owner: -
--

CREATE FUNCTION realtime.broadcast_changes(topic_name text, event_name text, operation text, table_name text, table_schema text, new record, old record, level text DEFAULT 'ROW'::text) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    -- Declare a variable to hold the JSONB representation of the row
    row_data jsonb := '{}'::jsonb;
BEGIN
    IF level = 'STATEMENT' THEN
        RAISE EXCEPTION 'function can only be triggered for each row, not for each statement';
    END IF;
    -- Check the operation type and handle accordingly
    IF operation = 'INSERT' OR operation = 'UPDATE' OR operation = 'DELETE' THEN
        row_data := jsonb_build_object('old_record', OLD, 'record', NEW, 'operation', operation, 'table', table_name, 'schema', table_schema);
        PERFORM realtime.send (row_data, event_name, topic_name);
    ELSE
        RAISE EXCEPTION 'Unexpected operation type: %', operation;
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Failed to process the row: %', SQLERRM;
END;

$$;


--
-- Name: build_prepared_statement_sql(text, regclass, realtime.wal_column[]); Type: FUNCTION; Schema: realtime; Owner: -
--

CREATE FUNCTION realtime.build_prepared_statement_sql(prepared_statement_name text, entity regclass, columns realtime.wal_column[]) RETURNS text
    LANGUAGE sql
    AS $$
      /*
      Builds a sql string that, if executed, creates a prepared statement to
      tests retrive a row from *entity* by its primary key columns.
      Example
          select realtime.build_prepared_statement_sql('public.notes', '{"id"}'::text[], '{"bigint"}'::text[])
      */
          select
      'prepare ' || prepared_statement_name || ' as
          select
              exists(
                  select
                      1
                  from
                      ' || entity || '
                  where
                      ' || string_agg(quote_ident(pkc.name) || '=' || quote_nullable(pkc.value #>> '{}') , ' and ') || '
              )'
          from
              unnest(columns) pkc
          where
              pkc.is_pkey
          group by
              entity
      $$;


--
-- Name: cast(text, regtype); Type: FUNCTION; Schema: realtime; Owner: -
--

CREATE FUNCTION realtime."cast"(val text, type_ regtype) RETURNS jsonb
    LANGUAGE plpgsql IMMUTABLE
    AS $$
declare
  res jsonb;
begin
  if type_::text = 'bytea' then
    return to_jsonb(val);
  end if;
  execute format('select to_jsonb(%L::'|| type_::text || ')', val) into res;
  return res;
end
$$;


--
-- Name: check_equality_op(realtime.equality_op, regtype, text, text); Type: FUNCTION; Schema: realtime; Owner: -
--

CREATE FUNCTION realtime.check_equality_op(op realtime.equality_op, type_ regtype, val_1 text, val_2 text) RETURNS boolean
    LANGUAGE plpgsql IMMUTABLE
    AS $$
      /*
      Casts *val_1* and *val_2* as type *type_* and check the *op* condition for truthiness
      */
      declare
          op_symbol text = (
              case
                  when op = 'eq' then '='
                  when op = 'neq' then '!='
                  when op = 'lt' then '<'
                  when op = 'lte' then '<='
                  when op = 'gt' then '>'
                  when op = 'gte' then '>='
                  when op = 'in' then '= any'
                  else 'UNKNOWN OP'
              end
          );
          res boolean;
      begin
          execute format(
              'select %L::'|| type_::text || ' ' || op_symbol
              || ' ( %L::'
              || (
                  case
                      when op = 'in' then type_::text || '[]'
                      else type_::text end
              )
              || ')', val_1, val_2) into res;
          return res;
      end;
      $$;


--
-- Name: is_visible_through_filters(realtime.wal_column[], realtime.user_defined_filter[]); Type: FUNCTION; Schema: realtime; Owner: -
--

CREATE FUNCTION realtime.is_visible_through_filters(columns realtime.wal_column[], filters realtime.user_defined_filter[]) RETURNS boolean
    LANGUAGE sql IMMUTABLE
    AS $_$
    /*
    Should the record be visible (true) or filtered out (false) after *filters* are applied
    */
        select
            -- Default to allowed when no filters present
            $2 is null -- no filters. this should not happen because subscriptions has a default
            or array_length($2, 1) is null -- array length of an empty array is null
            or bool_and(
                coalesce(
                    realtime.check_equality_op(
                        op:=f.op,
                        type_:=coalesce(
                            col.type_oid::regtype, -- null when wal2json version <= 2.4
                            col.type_name::regtype
                        ),
                        -- cast jsonb to text
                        val_1:=col.value #>> '{}',
                        val_2:=f.value
                    ),
                    false -- if null, filter does not match
                )
            )
        from
            unnest(filters) f
            join unnest(columns) col
                on f.column_name = col.name;
    $_$;


--
-- Name: list_changes(name, name, integer, integer); Type: FUNCTION; Schema: realtime; Owner: -
--

CREATE FUNCTION realtime.list_changes(publication name, slot_name name, max_changes integer, max_record_bytes integer) RETURNS TABLE(wal jsonb, is_rls_enabled boolean, subscription_ids uuid[], errors text[], slot_changes_count bigint)
    LANGUAGE sql
    SET log_min_messages TO 'fatal'
    AS $$
  WITH pub AS (
    SELECT
      concat_ws(
        ',',
        CASE WHEN bool_or(pubinsert) THEN 'insert' ELSE NULL END,
        CASE WHEN bool_or(pubupdate) THEN 'update' ELSE NULL END,
        CASE WHEN bool_or(pubdelete) THEN 'delete' ELSE NULL END
      ) AS w2j_actions,
      coalesce(
        string_agg(
          realtime.quote_wal2json(format('%I.%I', schemaname, tablename)::regclass),
          ','
        ) filter (WHERE ppt.tablename IS NOT NULL AND ppt.tablename NOT LIKE '% %'),
        ''
      ) AS w2j_add_tables
    FROM pg_publication pp
    LEFT JOIN pg_publication_tables ppt ON pp.pubname = ppt.pubname
    WHERE pp.pubname = publication
    GROUP BY pp.pubname
    LIMIT 1
  ),
  -- MATERIALIZED ensures pg_logical_slot_get_changes is called exactly once
  w2j AS MATERIALIZED (
    SELECT x.*, pub.w2j_add_tables
    FROM pub,
         pg_logical_slot_get_changes(
           slot_name, null, max_changes,
           'include-pk', 'true',
           'include-transaction', 'false',
           'include-timestamp', 'true',
           'include-type-oids', 'true',
           'format-version', '2',
           'actions', pub.w2j_actions,
           'add-tables', pub.w2j_add_tables
         ) x
  ),
  -- Count raw slot entries before apply_rls/subscription filter
  slot_count AS (
    SELECT count(*)::bigint AS cnt
    FROM w2j
    WHERE w2j.w2j_add_tables <> ''
  ),
  -- Apply RLS and filter as before
  rls_filtered AS (
    SELECT xyz.wal, xyz.is_rls_enabled, xyz.subscription_ids, xyz.errors
    FROM w2j,
         realtime.apply_rls(
           wal := w2j.data::jsonb,
           max_record_bytes := max_record_bytes
         ) xyz(wal, is_rls_enabled, subscription_ids, errors)
    WHERE w2j.w2j_add_tables <> ''
      AND xyz.subscription_ids[1] IS NOT NULL
  )
  -- Real rows with slot count attached
  SELECT rf.wal, rf.is_rls_enabled, rf.subscription_ids, rf.errors, sc.cnt
  FROM rls_filtered rf, slot_count sc

  UNION ALL

  -- Sentinel row: always returned when no real rows exist so Elixir can
  -- always read slot_changes_count. Identified by wal IS NULL.
  SELECT null, null, null, null, sc.cnt
  FROM slot_count sc
  WHERE NOT EXISTS (SELECT 1 FROM rls_filtered)
$$;


--
-- Name: quote_wal2json(regclass); Type: FUNCTION; Schema: realtime; Owner: -
--

CREATE FUNCTION realtime.quote_wal2json(entity regclass) RETURNS text
    LANGUAGE sql IMMUTABLE STRICT
    AS $$
      select
        (
          select string_agg('' || ch,'')
          from unnest(string_to_array(nsp.nspname::text, null)) with ordinality x(ch, idx)
          where
            not (x.idx = 1 and x.ch = '"')
            and not (
              x.idx = array_length(string_to_array(nsp.nspname::text, null), 1)
              and x.ch = '"'
            )
        )
        || '.'
        || (
          select string_agg('' || ch,'')
          from unnest(string_to_array(pc.relname::text, null)) with ordinality x(ch, idx)
          where
            not (x.idx = 1 and x.ch = '"')
            and not (
              x.idx = array_length(string_to_array(nsp.nspname::text, null), 1)
              and x.ch = '"'
            )
          )
      from
        pg_class pc
        join pg_namespace nsp
          on pc.relnamespace = nsp.oid
      where
        pc.oid = entity
    $$;


--
-- Name: send(jsonb, text, text, boolean); Type: FUNCTION; Schema: realtime; Owner: -
--

CREATE FUNCTION realtime.send(payload jsonb, event text, topic text, private boolean DEFAULT true) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
  generated_id uuid;
  final_payload jsonb;
BEGIN
  BEGIN
    -- Generate a new UUID for the id
    generated_id := gen_random_uuid();

    -- Check if payload has an 'id' key, if not, add the generated UUID
    IF payload ? 'id' THEN
      final_payload := payload;
    ELSE
      final_payload := jsonb_set(payload, '{id}', to_jsonb(generated_id));
    END IF;

    -- Set the topic configuration
    EXECUTE format('SET LOCAL realtime.topic TO %L', topic);

    -- Attempt to insert the message
    INSERT INTO realtime.messages (id, payload, event, topic, private, extension)
    VALUES (generated_id, final_payload, event, topic, private, 'broadcast');
  EXCEPTION
    WHEN OTHERS THEN
      -- Capture and notify the error
      RAISE WARNING 'ErrorSendingBroadcastMessage: %', SQLERRM;
  END;
END;
$$;


--
-- Name: subscription_check_filters(); Type: FUNCTION; Schema: realtime; Owner: -
--

CREATE FUNCTION realtime.subscription_check_filters() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    /*
    Validates that the user defined filters for a subscription:
    - refer to valid columns that the claimed role may access
    - values are coercable to the correct column type
    */
    declare
        col_names text[] = coalesce(
                array_agg(c.column_name order by c.ordinal_position),
                '{}'::text[]
            )
            from
                information_schema.columns c
            where
                format('%I.%I', c.table_schema, c.table_name)::regclass = new.entity
                and pg_catalog.has_column_privilege(
                    (new.claims ->> 'role'),
                    format('%I.%I', c.table_schema, c.table_name)::regclass,
                    c.column_name,
                    'SELECT'
                );
        filter realtime.user_defined_filter;
        col_type regtype;

        in_val jsonb;
    begin
        for filter in select * from unnest(new.filters) loop
            -- Filtered column is valid
            if not filter.column_name = any(col_names) then
                raise exception 'invalid column for filter %', filter.column_name;
            end if;

            -- Type is sanitized and safe for string interpolation
            col_type = (
                select atttypid::regtype
                from pg_catalog.pg_attribute
                where attrelid = new.entity
                      and attname = filter.column_name
            );
            if col_type is null then
                raise exception 'failed to lookup type for column %', filter.column_name;
            end if;

            -- Set maximum number of entries for in filter
            if filter.op = 'in'::realtime.equality_op then
                in_val = realtime.cast(filter.value, (col_type::text || '[]')::regtype);
                if coalesce(jsonb_array_length(in_val), 0) > 100 then
                    raise exception 'too many values for `in` filter. Maximum 100';
                end if;
            else
                -- raises an exception if value is not coercable to type
                perform realtime.cast(filter.value, col_type);
            end if;

        end loop;

        -- Apply consistent order to filters so the unique constraint on
        -- (subscription_id, entity, filters) can't be tricked by a different filter order
        new.filters = coalesce(
            array_agg(f order by f.column_name, f.op, f.value),
            '{}'
        ) from unnest(new.filters) f;

        return new;
    end;
    $$;


--
-- Name: to_regrole(text); Type: FUNCTION; Schema: realtime; Owner: -
--

CREATE FUNCTION realtime.to_regrole(role_name text) RETURNS regrole
    LANGUAGE sql IMMUTABLE
    AS $$ select role_name::regrole $$;


--
-- Name: topic(); Type: FUNCTION; Schema: realtime; Owner: -
--

CREATE FUNCTION realtime.topic() RETURNS text
    LANGUAGE sql STABLE
    AS $$
select nullif(current_setting('realtime.topic', true), '')::text;
$$;


--
-- Name: allow_any_operation(text[]); Type: FUNCTION; Schema: storage; Owner: -
--

CREATE FUNCTION storage.allow_any_operation(expected_operations text[]) RETURNS boolean
    LANGUAGE sql STABLE
    AS $$
  WITH current_operation AS (
    SELECT storage.operation() AS raw_operation
  ),
  normalized AS (
    SELECT CASE
      WHEN raw_operation LIKE 'storage.%' THEN substr(raw_operation, 9)
      ELSE raw_operation
    END AS current_operation
    FROM current_operation
  )
  SELECT EXISTS (
    SELECT 1
    FROM normalized n
    CROSS JOIN LATERAL unnest(expected_operations) AS expected_operation
    WHERE expected_operation IS NOT NULL
      AND expected_operation <> ''
      AND n.current_operation = CASE
        WHEN expected_operation LIKE 'storage.%' THEN substr(expected_operation, 9)
        ELSE expected_operation
      END
  );
$$;


--
-- Name: allow_only_operation(text); Type: FUNCTION; Schema: storage; Owner: -
--

CREATE FUNCTION storage.allow_only_operation(expected_operation text) RETURNS boolean
    LANGUAGE sql STABLE
    AS $$
  WITH current_operation AS (
    SELECT storage.operation() AS raw_operation
  ),
  normalized AS (
    SELECT
      CASE
        WHEN raw_operation LIKE 'storage.%' THEN substr(raw_operation, 9)
        ELSE raw_operation
      END AS current_operation,
      CASE
        WHEN expected_operation LIKE 'storage.%' THEN substr(expected_operation, 9)
        ELSE expected_operation
      END AS requested_operation
    FROM current_operation
  )
  SELECT CASE
    WHEN requested_operation IS NULL OR requested_operation = '' THEN FALSE
    ELSE COALESCE(current_operation = requested_operation, FALSE)
  END
  FROM normalized;
$$;


--
-- Name: can_insert_object(text, text, uuid, jsonb); Type: FUNCTION; Schema: storage; Owner: -
--

CREATE FUNCTION storage.can_insert_object(bucketid text, name text, owner uuid, metadata jsonb) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
  INSERT INTO "storage"."objects" ("bucket_id", "name", "owner", "metadata") VALUES (bucketid, name, owner, metadata);
  -- hack to rollback the successful insert
  RAISE sqlstate 'PT200' using
  message = 'ROLLBACK',
  detail = 'rollback successful insert';
END
$$;


--
-- Name: enforce_bucket_name_length(); Type: FUNCTION; Schema: storage; Owner: -
--

CREATE FUNCTION storage.enforce_bucket_name_length() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
begin
    if length(new.name) > 100 then
        raise exception 'bucket name "%" is too long (% characters). Max is 100.', new.name, length(new.name);
    end if;
    return new;
end;
$$;


--
-- Name: extension(text); Type: FUNCTION; Schema: storage; Owner: -
--

CREATE FUNCTION storage.extension(name text) RETURNS text
    LANGUAGE plpgsql IMMUTABLE
    AS $$
DECLARE
    _parts text[];
    _filename text;
BEGIN
    -- Split on "/" to get path segments
    SELECT string_to_array(name, '/') INTO _parts;
    -- Get the last path segment (the actual filename)
    SELECT _parts[array_length(_parts, 1)] INTO _filename;
    -- Extract extension: reverse, split on '.', then reverse again
    RETURN reverse(split_part(reverse(_filename), '.', 1));
END
$$;


--
-- Name: filename(text); Type: FUNCTION; Schema: storage; Owner: -
--

CREATE FUNCTION storage.filename(name text) RETURNS text
    LANGUAGE plpgsql
    AS $$
DECLARE
_parts text[];
BEGIN
	select string_to_array(name, '/') into _parts;
	return _parts[array_length(_parts,1)];
END
$$;


--
-- Name: foldername(text); Type: FUNCTION; Schema: storage; Owner: -
--

CREATE FUNCTION storage.foldername(name text) RETURNS text[]
    LANGUAGE plpgsql IMMUTABLE
    AS $$
DECLARE
    _parts text[];
BEGIN
    -- Split on "/" to get path segments
    SELECT string_to_array(name, '/') INTO _parts;
    -- Return everything except the last segment
    RETURN _parts[1 : array_length(_parts,1) - 1];
END
$$;


--
-- Name: get_common_prefix(text, text, text); Type: FUNCTION; Schema: storage; Owner: -
--

CREATE FUNCTION storage.get_common_prefix(p_key text, p_prefix text, p_delimiter text) RETURNS text
    LANGUAGE sql IMMUTABLE
    AS $$
SELECT CASE
    WHEN position(p_delimiter IN substring(p_key FROM length(p_prefix) + 1)) > 0
    THEN left(p_key, length(p_prefix) + position(p_delimiter IN substring(p_key FROM length(p_prefix) + 1)))
    ELSE NULL
END;
$$;


--
-- Name: get_size_by_bucket(); Type: FUNCTION; Schema: storage; Owner: -
--

CREATE FUNCTION storage.get_size_by_bucket() RETURNS TABLE(size bigint, bucket_id text)
    LANGUAGE plpgsql STABLE
    AS $$
BEGIN
    return query
        select sum((metadata->>'size')::bigint)::bigint as size, obj.bucket_id
        from "storage".objects as obj
        group by obj.bucket_id;
END
$$;


--
-- Name: list_multipart_uploads_with_delimiter(text, text, text, integer, text, text); Type: FUNCTION; Schema: storage; Owner: -
--

CREATE FUNCTION storage.list_multipart_uploads_with_delimiter(bucket_id text, prefix_param text, delimiter_param text, max_keys integer DEFAULT 100, next_key_token text DEFAULT ''::text, next_upload_token text DEFAULT ''::text) RETURNS TABLE(key text, id text, created_at timestamp with time zone)
    LANGUAGE plpgsql
    AS $_$
BEGIN
    RETURN QUERY EXECUTE
        'SELECT DISTINCT ON(key COLLATE "C") * from (
            SELECT
                CASE
                    WHEN position($2 IN substring(key from length($1) + 1)) > 0 THEN
                        substring(key from 1 for length($1) + position($2 IN substring(key from length($1) + 1)))
                    ELSE
                        key
                END AS key, id, created_at
            FROM
                storage.s3_multipart_uploads
            WHERE
                bucket_id = $5 AND
                key ILIKE $1 || ''%'' AND
                CASE
                    WHEN $4 != '''' AND $6 = '''' THEN
                        CASE
                            WHEN position($2 IN substring(key from length($1) + 1)) > 0 THEN
                                substring(key from 1 for length($1) + position($2 IN substring(key from length($1) + 1))) COLLATE "C" > $4
                            ELSE
                                key COLLATE "C" > $4
                            END
                    ELSE
                        true
                END AND
                CASE
                    WHEN $6 != '''' THEN
                        id COLLATE "C" > $6
                    ELSE
                        true
                    END
            ORDER BY
                key COLLATE "C" ASC, created_at ASC) as e order by key COLLATE "C" LIMIT $3'
        USING prefix_param, delimiter_param, max_keys, next_key_token, bucket_id, next_upload_token;
END;
$_$;


--
-- Name: list_objects_with_delimiter(text, text, text, integer, text, text, text); Type: FUNCTION; Schema: storage; Owner: -
--

CREATE FUNCTION storage.list_objects_with_delimiter(_bucket_id text, prefix_param text, delimiter_param text, max_keys integer DEFAULT 100, start_after text DEFAULT ''::text, next_token text DEFAULT ''::text, sort_order text DEFAULT 'asc'::text) RETURNS TABLE(name text, id uuid, metadata jsonb, updated_at timestamp with time zone, created_at timestamp with time zone, last_accessed_at timestamp with time zone)
    LANGUAGE plpgsql STABLE
    AS $_$
DECLARE
    v_peek_name TEXT;
    v_current RECORD;
    v_common_prefix TEXT;

    -- Configuration
    v_is_asc BOOLEAN;
    v_prefix TEXT;
    v_start TEXT;
    v_upper_bound TEXT;
    v_file_batch_size INT;

    -- Seek state
    v_next_seek TEXT;
    v_count INT := 0;

    -- Dynamic SQL for batch query only
    v_batch_query TEXT;

BEGIN
    -- ========================================================================
    -- INITIALIZATION
    -- ========================================================================
    v_is_asc := lower(coalesce(sort_order, 'asc')) = 'asc';
    v_prefix := coalesce(prefix_param, '');
    v_start := CASE WHEN coalesce(next_token, '') <> '' THEN next_token ELSE coalesce(start_after, '') END;
    v_file_batch_size := LEAST(GREATEST(max_keys * 2, 100), 1000);

    -- Calculate upper bound for prefix filtering (bytewise, using COLLATE "C")
    IF v_prefix = '' THEN
        v_upper_bound := NULL;
    ELSIF right(v_prefix, 1) = delimiter_param THEN
        v_upper_bound := left(v_prefix, -1) || chr(ascii(delimiter_param) + 1);
    ELSE
        v_upper_bound := left(v_prefix, -1) || chr(ascii(right(v_prefix, 1)) + 1);
    END IF;

    -- Build batch query (dynamic SQL - called infrequently, amortized over many rows)
    IF v_is_asc THEN
        IF v_upper_bound IS NOT NULL THEN
            v_batch_query := 'SELECT o.name, o.id, o.updated_at, o.created_at, o.last_accessed_at, o.metadata ' ||
                'FROM storage.objects o WHERE o.bucket_id = $1 AND o.name COLLATE "C" >= $2 ' ||
                'AND o.name COLLATE "C" < $3 ORDER BY o.name COLLATE "C" ASC LIMIT $4';
        ELSE
            v_batch_query := 'SELECT o.name, o.id, o.updated_at, o.created_at, o.last_accessed_at, o.metadata ' ||
                'FROM storage.objects o WHERE o.bucket_id = $1 AND o.name COLLATE "C" >= $2 ' ||
                'ORDER BY o.name COLLATE "C" ASC LIMIT $4';
        END IF;
    ELSE
        IF v_upper_bound IS NOT NULL THEN
            v_batch_query := 'SELECT o.name, o.id, o.updated_at, o.created_at, o.last_accessed_at, o.metadata ' ||
                'FROM storage.objects o WHERE o.bucket_id = $1 AND o.name COLLATE "C" < $2 ' ||
                'AND o.name COLLATE "C" >= $3 ORDER BY o.name COLLATE "C" DESC LIMIT $4';
        ELSE
            v_batch_query := 'SELECT o.name, o.id, o.updated_at, o.created_at, o.last_accessed_at, o.metadata ' ||
                'FROM storage.objects o WHERE o.bucket_id = $1 AND o.name COLLATE "C" < $2 ' ||
                'ORDER BY o.name COLLATE "C" DESC LIMIT $4';
        END IF;
    END IF;

    -- ========================================================================
    -- SEEK INITIALIZATION: Determine starting position
    -- ========================================================================
    IF v_start = '' THEN
        IF v_is_asc THEN
            v_next_seek := v_prefix;
        ELSE
            -- DESC without cursor: find the last item in range
            IF v_upper_bound IS NOT NULL THEN
                SELECT o.name INTO v_next_seek FROM storage.objects o
                WHERE o.bucket_id = _bucket_id AND o.name COLLATE "C" >= v_prefix AND o.name COLLATE "C" < v_upper_bound
                ORDER BY o.name COLLATE "C" DESC LIMIT 1;
            ELSIF v_prefix <> '' THEN
                SELECT o.name INTO v_next_seek FROM storage.objects o
                WHERE o.bucket_id = _bucket_id AND o.name COLLATE "C" >= v_prefix
                ORDER BY o.name COLLATE "C" DESC LIMIT 1;
            ELSE
                SELECT o.name INTO v_next_seek FROM storage.objects o
                WHERE o.bucket_id = _bucket_id
                ORDER BY o.name COLLATE "C" DESC LIMIT 1;
            END IF;

            IF v_next_seek IS NOT NULL THEN
                v_next_seek := v_next_seek || delimiter_param;
            ELSE
                RETURN;
            END IF;
        END IF;
    ELSE
        -- Cursor provided: determine if it refers to a folder or leaf
        IF EXISTS (
            SELECT 1 FROM storage.objects o
            WHERE o.bucket_id = _bucket_id
              AND o.name COLLATE "C" LIKE v_start || delimiter_param || '%'
            LIMIT 1
        ) THEN
            -- Cursor refers to a folder
            IF v_is_asc THEN
                v_next_seek := v_start || chr(ascii(delimiter_param) + 1);
            ELSE
                v_next_seek := v_start || delimiter_param;
            END IF;
        ELSE
            -- Cursor refers to a leaf object
            IF v_is_asc THEN
                v_next_seek := v_start || delimiter_param;
            ELSE
                v_next_seek := v_start;
            END IF;
        END IF;
    END IF;

    -- ========================================================================
    -- MAIN LOOP: Hybrid peek-then-batch algorithm
    -- Uses STATIC SQL for peek (hot path) and DYNAMIC SQL for batch
    -- ========================================================================
    LOOP
        EXIT WHEN v_count >= max_keys;

        -- STEP 1: PEEK using STATIC SQL (plan cached, very fast)
        IF v_is_asc THEN
            IF v_upper_bound IS NOT NULL THEN
                SELECT o.name INTO v_peek_name FROM storage.objects o
                WHERE o.bucket_id = _bucket_id AND o.name COLLATE "C" >= v_next_seek AND o.name COLLATE "C" < v_upper_bound
                ORDER BY o.name COLLATE "C" ASC LIMIT 1;
            ELSE
                SELECT o.name INTO v_peek_name FROM storage.objects o
                WHERE o.bucket_id = _bucket_id AND o.name COLLATE "C" >= v_next_seek
                ORDER BY o.name COLLATE "C" ASC LIMIT 1;
            END IF;
        ELSE
            IF v_upper_bound IS NOT NULL THEN
                SELECT o.name INTO v_peek_name FROM storage.objects o
                WHERE o.bucket_id = _bucket_id AND o.name COLLATE "C" < v_next_seek AND o.name COLLATE "C" >= v_prefix
                ORDER BY o.name COLLATE "C" DESC LIMIT 1;
            ELSIF v_prefix <> '' THEN
                SELECT o.name INTO v_peek_name FROM storage.objects o
                WHERE o.bucket_id = _bucket_id AND o.name COLLATE "C" < v_next_seek AND o.name COLLATE "C" >= v_prefix
                ORDER BY o.name COLLATE "C" DESC LIMIT 1;
            ELSE
                SELECT o.name INTO v_peek_name FROM storage.objects o
                WHERE o.bucket_id = _bucket_id AND o.name COLLATE "C" < v_next_seek
                ORDER BY o.name COLLATE "C" DESC LIMIT 1;
            END IF;
        END IF;

        EXIT WHEN v_peek_name IS NULL;

        -- STEP 2: Check if this is a FOLDER or FILE
        v_common_prefix := storage.get_common_prefix(v_peek_name, v_prefix, delimiter_param);

        IF v_common_prefix IS NOT NULL THEN
            -- FOLDER: Emit and skip to next folder (no heap access needed)
            name := rtrim(v_common_prefix, delimiter_param);
            id := NULL;
            updated_at := NULL;
            created_at := NULL;
            last_accessed_at := NULL;
            metadata := NULL;
            RETURN NEXT;
            v_count := v_count + 1;

            -- Advance seek past the folder range
            IF v_is_asc THEN
                v_next_seek := left(v_common_prefix, -1) || chr(ascii(delimiter_param) + 1);
            ELSE
                v_next_seek := v_common_prefix;
            END IF;
        ELSE
            -- FILE: Batch fetch using DYNAMIC SQL (overhead amortized over many rows)
            -- For ASC: upper_bound is the exclusive upper limit (< condition)
            -- For DESC: prefix is the inclusive lower limit (>= condition)
            FOR v_current IN EXECUTE v_batch_query USING _bucket_id, v_next_seek,
                CASE WHEN v_is_asc THEN COALESCE(v_upper_bound, v_prefix) ELSE v_prefix END, v_file_batch_size
            LOOP
                v_common_prefix := storage.get_common_prefix(v_current.name, v_prefix, delimiter_param);

                IF v_common_prefix IS NOT NULL THEN
                    -- Hit a folder: exit batch, let peek handle it
                    v_next_seek := v_current.name;
                    EXIT;
                END IF;

                -- Emit file
                name := v_current.name;
                id := v_current.id;
                updated_at := v_current.updated_at;
                created_at := v_current.created_at;
                last_accessed_at := v_current.last_accessed_at;
                metadata := v_current.metadata;
                RETURN NEXT;
                v_count := v_count + 1;

                -- Advance seek past this file
                IF v_is_asc THEN
                    v_next_seek := v_current.name || delimiter_param;
                ELSE
                    v_next_seek := v_current.name;
                END IF;

                EXIT WHEN v_count >= max_keys;
            END LOOP;
        END IF;
    END LOOP;
END;
$_$;


--
-- Name: operation(); Type: FUNCTION; Schema: storage; Owner: -
--

CREATE FUNCTION storage.operation() RETURNS text
    LANGUAGE plpgsql STABLE
    AS $$
BEGIN
    RETURN current_setting('storage.operation', true);
END;
$$;


--
-- Name: protect_delete(); Type: FUNCTION; Schema: storage; Owner: -
--

CREATE FUNCTION storage.protect_delete() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- Check if storage.allow_delete_query is set to 'true'
    IF COALESCE(current_setting('storage.allow_delete_query', true), 'false') != 'true' THEN
        RAISE EXCEPTION 'Direct deletion from storage tables is not allowed. Use the Storage API instead.'
            USING HINT = 'This prevents accidental data loss from orphaned objects.',
                  ERRCODE = '42501';
    END IF;
    RETURN NULL;
END;
$$;


--
-- Name: search(text, text, integer, integer, integer, text, text, text); Type: FUNCTION; Schema: storage; Owner: -
--

CREATE FUNCTION storage.search(prefix text, bucketname text, limits integer DEFAULT 100, levels integer DEFAULT 1, offsets integer DEFAULT 0, search text DEFAULT ''::text, sortcolumn text DEFAULT 'name'::text, sortorder text DEFAULT 'asc'::text) RETURNS TABLE(name text, id uuid, updated_at timestamp with time zone, created_at timestamp with time zone, last_accessed_at timestamp with time zone, metadata jsonb)
    LANGUAGE plpgsql STABLE
    AS $_$
DECLARE
    v_peek_name TEXT;
    v_current RECORD;
    v_common_prefix TEXT;
    v_delimiter CONSTANT TEXT := '/';

    -- Configuration
    v_limit INT;
    v_prefix TEXT;
    v_prefix_lower TEXT;
    v_is_asc BOOLEAN;
    v_order_by TEXT;
    v_sort_order TEXT;
    v_upper_bound TEXT;
    v_file_batch_size INT;

    -- Dynamic SQL for batch query only
    v_batch_query TEXT;

    -- Seek state
    v_next_seek TEXT;
    v_count INT := 0;
    v_skipped INT := 0;
BEGIN
    -- ========================================================================
    -- INITIALIZATION
    -- ========================================================================
    v_limit := LEAST(coalesce(limits, 100), 1500);
    v_prefix := coalesce(prefix, '') || coalesce(search, '');
    v_prefix_lower := lower(v_prefix);
    v_is_asc := lower(coalesce(sortorder, 'asc')) = 'asc';
    v_file_batch_size := LEAST(GREATEST(v_limit * 2, 100), 1000);

    -- Validate sort column
    CASE lower(coalesce(sortcolumn, 'name'))
        WHEN 'name' THEN v_order_by := 'name';
        WHEN 'updated_at' THEN v_order_by := 'updated_at';
        WHEN 'created_at' THEN v_order_by := 'created_at';
        WHEN 'last_accessed_at' THEN v_order_by := 'last_accessed_at';
        ELSE v_order_by := 'name';
    END CASE;

    v_sort_order := CASE WHEN v_is_asc THEN 'asc' ELSE 'desc' END;

    -- ========================================================================
    -- NON-NAME SORTING: Use path_tokens approach (unchanged)
    -- ========================================================================
    IF v_order_by != 'name' THEN
        RETURN QUERY EXECUTE format(
            $sql$
            WITH folders AS (
                SELECT path_tokens[$1] AS folder
                FROM storage.objects
                WHERE objects.name ILIKE $2 || '%%'
                  AND bucket_id = $3
                  AND array_length(objects.path_tokens, 1) <> $1
                GROUP BY folder
                ORDER BY folder %s
            )
            (SELECT folder AS "name",
                   NULL::uuid AS id,
                   NULL::timestamptz AS updated_at,
                   NULL::timestamptz AS created_at,
                   NULL::timestamptz AS last_accessed_at,
                   NULL::jsonb AS metadata FROM folders)
            UNION ALL
            (SELECT path_tokens[$1] AS "name",
                   id, updated_at, created_at, last_accessed_at, metadata
             FROM storage.objects
             WHERE objects.name ILIKE $2 || '%%'
               AND bucket_id = $3
               AND array_length(objects.path_tokens, 1) = $1
             ORDER BY %I %s)
            LIMIT $4 OFFSET $5
            $sql$, v_sort_order, v_order_by, v_sort_order
        ) USING levels, v_prefix, bucketname, v_limit, offsets;
        RETURN;
    END IF;

    -- ========================================================================
    -- NAME SORTING: Hybrid skip-scan with batch optimization
    -- ========================================================================

    -- Calculate upper bound for prefix filtering
    IF v_prefix_lower = '' THEN
        v_upper_bound := NULL;
    ELSIF right(v_prefix_lower, 1) = v_delimiter THEN
        v_upper_bound := left(v_prefix_lower, -1) || chr(ascii(v_delimiter) + 1);
    ELSE
        v_upper_bound := left(v_prefix_lower, -1) || chr(ascii(right(v_prefix_lower, 1)) + 1);
    END IF;

    -- Build batch query (dynamic SQL - called infrequently, amortized over many rows)
    IF v_is_asc THEN
        IF v_upper_bound IS NOT NULL THEN
            v_batch_query := 'SELECT o.name, o.id, o.updated_at, o.created_at, o.last_accessed_at, o.metadata ' ||
                'FROM storage.objects o WHERE o.bucket_id = $1 AND lower(o.name) COLLATE "C" >= $2 ' ||
                'AND lower(o.name) COLLATE "C" < $3 ORDER BY lower(o.name) COLLATE "C" ASC LIMIT $4';
        ELSE
            v_batch_query := 'SELECT o.name, o.id, o.updated_at, o.created_at, o.last_accessed_at, o.metadata ' ||
                'FROM storage.objects o WHERE o.bucket_id = $1 AND lower(o.name) COLLATE "C" >= $2 ' ||
                'ORDER BY lower(o.name) COLLATE "C" ASC LIMIT $4';
        END IF;
    ELSE
        IF v_upper_bound IS NOT NULL THEN
            v_batch_query := 'SELECT o.name, o.id, o.updated_at, o.created_at, o.last_accessed_at, o.metadata ' ||
                'FROM storage.objects o WHERE o.bucket_id = $1 AND lower(o.name) COLLATE "C" < $2 ' ||
                'AND lower(o.name) COLLATE "C" >= $3 ORDER BY lower(o.name) COLLATE "C" DESC LIMIT $4';
        ELSE
            v_batch_query := 'SELECT o.name, o.id, o.updated_at, o.created_at, o.last_accessed_at, o.metadata ' ||
                'FROM storage.objects o WHERE o.bucket_id = $1 AND lower(o.name) COLLATE "C" < $2 ' ||
                'ORDER BY lower(o.name) COLLATE "C" DESC LIMIT $4';
        END IF;
    END IF;

    -- Initialize seek position
    IF v_is_asc THEN
        v_next_seek := v_prefix_lower;
    ELSE
        -- DESC: find the last item in range first (static SQL)
        IF v_upper_bound IS NOT NULL THEN
            SELECT o.name INTO v_peek_name FROM storage.objects o
            WHERE o.bucket_id = bucketname AND lower(o.name) COLLATE "C" >= v_prefix_lower AND lower(o.name) COLLATE "C" < v_upper_bound
            ORDER BY lower(o.name) COLLATE "C" DESC LIMIT 1;
        ELSIF v_prefix_lower <> '' THEN
            SELECT o.name INTO v_peek_name FROM storage.objects o
            WHERE o.bucket_id = bucketname AND lower(o.name) COLLATE "C" >= v_prefix_lower
            ORDER BY lower(o.name) COLLATE "C" DESC LIMIT 1;
        ELSE
            SELECT o.name INTO v_peek_name FROM storage.objects o
            WHERE o.bucket_id = bucketname
            ORDER BY lower(o.name) COLLATE "C" DESC LIMIT 1;
        END IF;

        IF v_peek_name IS NOT NULL THEN
            v_next_seek := lower(v_peek_name) || v_delimiter;
        ELSE
            RETURN;
        END IF;
    END IF;

    -- ========================================================================
    -- MAIN LOOP: Hybrid peek-then-batch algorithm
    -- Uses STATIC SQL for peek (hot path) and DYNAMIC SQL for batch
    -- ========================================================================
    LOOP
        EXIT WHEN v_count >= v_limit;

        -- STEP 1: PEEK using STATIC SQL (plan cached, very fast)
        IF v_is_asc THEN
            IF v_upper_bound IS NOT NULL THEN
                SELECT o.name INTO v_peek_name FROM storage.objects o
                WHERE o.bucket_id = bucketname AND lower(o.name) COLLATE "C" >= v_next_seek AND lower(o.name) COLLATE "C" < v_upper_bound
                ORDER BY lower(o.name) COLLATE "C" ASC LIMIT 1;
            ELSE
                SELECT o.name INTO v_peek_name FROM storage.objects o
                WHERE o.bucket_id = bucketname AND lower(o.name) COLLATE "C" >= v_next_seek
                ORDER BY lower(o.name) COLLATE "C" ASC LIMIT 1;
            END IF;
        ELSE
            IF v_upper_bound IS NOT NULL THEN
                SELECT o.name INTO v_peek_name FROM storage.objects o
                WHERE o.bucket_id = bucketname AND lower(o.name) COLLATE "C" < v_next_seek AND lower(o.name) COLLATE "C" >= v_prefix_lower
                ORDER BY lower(o.name) COLLATE "C" DESC LIMIT 1;
            ELSIF v_prefix_lower <> '' THEN
                SELECT o.name INTO v_peek_name FROM storage.objects o
                WHERE o.bucket_id = bucketname AND lower(o.name) COLLATE "C" < v_next_seek AND lower(o.name) COLLATE "C" >= v_prefix_lower
                ORDER BY lower(o.name) COLLATE "C" DESC LIMIT 1;
            ELSE
                SELECT o.name INTO v_peek_name FROM storage.objects o
                WHERE o.bucket_id = bucketname AND lower(o.name) COLLATE "C" < v_next_seek
                ORDER BY lower(o.name) COLLATE "C" DESC LIMIT 1;
            END IF;
        END IF;

        EXIT WHEN v_peek_name IS NULL;

        -- STEP 2: Check if this is a FOLDER or FILE
        v_common_prefix := storage.get_common_prefix(lower(v_peek_name), v_prefix_lower, v_delimiter);

        IF v_common_prefix IS NOT NULL THEN
            -- FOLDER: Handle offset, emit if needed, skip to next folder
            IF v_skipped < offsets THEN
                v_skipped := v_skipped + 1;
            ELSE
                name := split_part(rtrim(storage.get_common_prefix(v_peek_name, v_prefix, v_delimiter), v_delimiter), v_delimiter, levels);
                id := NULL;
                updated_at := NULL;
                created_at := NULL;
                last_accessed_at := NULL;
                metadata := NULL;
                RETURN NEXT;
                v_count := v_count + 1;
            END IF;

            -- Advance seek past the folder range
            IF v_is_asc THEN
                v_next_seek := lower(left(v_common_prefix, -1)) || chr(ascii(v_delimiter) + 1);
            ELSE
                v_next_seek := lower(v_common_prefix);
            END IF;
        ELSE
            -- FILE: Batch fetch using DYNAMIC SQL (overhead amortized over many rows)
            -- For ASC: upper_bound is the exclusive upper limit (< condition)
            -- For DESC: prefix_lower is the inclusive lower limit (>= condition)
            FOR v_current IN EXECUTE v_batch_query
                USING bucketname, v_next_seek,
                    CASE WHEN v_is_asc THEN COALESCE(v_upper_bound, v_prefix_lower) ELSE v_prefix_lower END, v_file_batch_size
            LOOP
                v_common_prefix := storage.get_common_prefix(lower(v_current.name), v_prefix_lower, v_delimiter);

                IF v_common_prefix IS NOT NULL THEN
                    -- Hit a folder: exit batch, let peek handle it
                    v_next_seek := lower(v_current.name);
                    EXIT;
                END IF;

                -- Handle offset skipping
                IF v_skipped < offsets THEN
                    v_skipped := v_skipped + 1;
                ELSE
                    -- Emit file
                    name := split_part(v_current.name, v_delimiter, levels);
                    id := v_current.id;
                    updated_at := v_current.updated_at;
                    created_at := v_current.created_at;
                    last_accessed_at := v_current.last_accessed_at;
                    metadata := v_current.metadata;
                    RETURN NEXT;
                    v_count := v_count + 1;
                END IF;

                -- Advance seek past this file
                IF v_is_asc THEN
                    v_next_seek := lower(v_current.name) || v_delimiter;
                ELSE
                    v_next_seek := lower(v_current.name);
                END IF;

                EXIT WHEN v_count >= v_limit;
            END LOOP;
        END IF;
    END LOOP;
END;
$_$;


--
-- Name: search_by_timestamp(text, text, integer, integer, text, text, text, text); Type: FUNCTION; Schema: storage; Owner: -
--

CREATE FUNCTION storage.search_by_timestamp(p_prefix text, p_bucket_id text, p_limit integer, p_level integer, p_start_after text, p_sort_order text, p_sort_column text, p_sort_column_after text) RETURNS TABLE(key text, name text, id uuid, updated_at timestamp with time zone, created_at timestamp with time zone, last_accessed_at timestamp with time zone, metadata jsonb)
    LANGUAGE plpgsql STABLE
    AS $_$
DECLARE
    v_cursor_op text;
    v_query text;
    v_prefix text;
BEGIN
    v_prefix := coalesce(p_prefix, '');

    IF p_sort_order = 'asc' THEN
        v_cursor_op := '>';
    ELSE
        v_cursor_op := '<';
    END IF;

    v_query := format($sql$
        WITH raw_objects AS (
            SELECT
                o.name AS obj_name,
                o.id AS obj_id,
                o.updated_at AS obj_updated_at,
                o.created_at AS obj_created_at,
                o.last_accessed_at AS obj_last_accessed_at,
                o.metadata AS obj_metadata,
                storage.get_common_prefix(o.name, $1, '/') AS common_prefix
            FROM storage.objects o
            WHERE o.bucket_id = $2
              AND o.name COLLATE "C" LIKE $1 || '%%'
        ),
        -- Aggregate common prefixes (folders)
        -- Both created_at and updated_at use MIN(obj_created_at) to match the old prefixes table behavior
        aggregated_prefixes AS (
            SELECT
                rtrim(common_prefix, '/') AS name,
                NULL::uuid AS id,
                MIN(obj_created_at) AS updated_at,
                MIN(obj_created_at) AS created_at,
                NULL::timestamptz AS last_accessed_at,
                NULL::jsonb AS metadata,
                TRUE AS is_prefix
            FROM raw_objects
            WHERE common_prefix IS NOT NULL
            GROUP BY common_prefix
        ),
        leaf_objects AS (
            SELECT
                obj_name AS name,
                obj_id AS id,
                obj_updated_at AS updated_at,
                obj_created_at AS created_at,
                obj_last_accessed_at AS last_accessed_at,
                obj_metadata AS metadata,
                FALSE AS is_prefix
            FROM raw_objects
            WHERE common_prefix IS NULL
        ),
        combined AS (
            SELECT * FROM aggregated_prefixes
            UNION ALL
            SELECT * FROM leaf_objects
        ),
        filtered AS (
            SELECT *
            FROM combined
            WHERE (
                $5 = ''
                OR ROW(
                    date_trunc('milliseconds', %I),
                    name COLLATE "C"
                ) %s ROW(
                    COALESCE(NULLIF($6, '')::timestamptz, 'epoch'::timestamptz),
                    $5
                )
            )
        )
        SELECT
            split_part(name, '/', $3) AS key,
            name,
            id,
            updated_at,
            created_at,
            last_accessed_at,
            metadata
        FROM filtered
        ORDER BY
            COALESCE(date_trunc('milliseconds', %I), 'epoch'::timestamptz) %s,
            name COLLATE "C" %s
        LIMIT $4
    $sql$,
        p_sort_column,
        v_cursor_op,
        p_sort_column,
        p_sort_order,
        p_sort_order
    );

    RETURN QUERY EXECUTE v_query
    USING v_prefix, p_bucket_id, p_level, p_limit, p_start_after, p_sort_column_after;
END;
$_$;


--
-- Name: search_v2(text, text, integer, integer, text, text, text, text); Type: FUNCTION; Schema: storage; Owner: -
--

CREATE FUNCTION storage.search_v2(prefix text, bucket_name text, limits integer DEFAULT 100, levels integer DEFAULT 1, start_after text DEFAULT ''::text, sort_order text DEFAULT 'asc'::text, sort_column text DEFAULT 'name'::text, sort_column_after text DEFAULT ''::text) RETURNS TABLE(key text, name text, id uuid, updated_at timestamp with time zone, created_at timestamp with time zone, last_accessed_at timestamp with time zone, metadata jsonb)
    LANGUAGE plpgsql STABLE
    AS $$
DECLARE
    v_sort_col text;
    v_sort_ord text;
    v_limit int;
BEGIN
    -- Cap limit to maximum of 1500 records
    v_limit := LEAST(coalesce(limits, 100), 1500);

    -- Validate and normalize sort_order
    v_sort_ord := lower(coalesce(sort_order, 'asc'));
    IF v_sort_ord NOT IN ('asc', 'desc') THEN
        v_sort_ord := 'asc';
    END IF;

    -- Validate and normalize sort_column
    v_sort_col := lower(coalesce(sort_column, 'name'));
    IF v_sort_col NOT IN ('name', 'updated_at', 'created_at') THEN
        v_sort_col := 'name';
    END IF;

    -- Route to appropriate implementation
    IF v_sort_col = 'name' THEN
        -- Use list_objects_with_delimiter for name sorting (most efficient: O(k * log n))
        RETURN QUERY
        SELECT
            split_part(l.name, '/', levels) AS key,
            l.name AS name,
            l.id,
            l.updated_at,
            l.created_at,
            l.last_accessed_at,
            l.metadata
        FROM storage.list_objects_with_delimiter(
            bucket_name,
            coalesce(prefix, ''),
            '/',
            v_limit,
            start_after,
            '',
            v_sort_ord
        ) l;
    ELSE
        -- Use aggregation approach for timestamp sorting
        -- Not efficient for large datasets but supports correct pagination
        RETURN QUERY SELECT * FROM storage.search_by_timestamp(
            prefix, bucket_name, v_limit, levels, start_after,
            v_sort_ord, v_sort_col, sort_column_after
        );
    END IF;
END;
$$;


--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: storage; Owner: -
--

CREATE FUNCTION storage.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW; 
END;
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: audit_log_entries; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.audit_log_entries (
    instance_id uuid,
    id uuid NOT NULL,
    payload json,
    created_at timestamp with time zone,
    ip_address character varying(64) DEFAULT ''::character varying NOT NULL
);


--
-- Name: TABLE audit_log_entries; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON TABLE auth.audit_log_entries IS 'Auth: Audit trail for user actions.';


--
-- Name: custom_oauth_providers; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.custom_oauth_providers (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    provider_type text NOT NULL,
    identifier text NOT NULL,
    name text NOT NULL,
    client_id text NOT NULL,
    client_secret text NOT NULL,
    acceptable_client_ids text[] DEFAULT '{}'::text[] NOT NULL,
    scopes text[] DEFAULT '{}'::text[] NOT NULL,
    pkce_enabled boolean DEFAULT true NOT NULL,
    attribute_mapping jsonb DEFAULT '{}'::jsonb NOT NULL,
    authorization_params jsonb DEFAULT '{}'::jsonb NOT NULL,
    enabled boolean DEFAULT true NOT NULL,
    email_optional boolean DEFAULT false NOT NULL,
    issuer text,
    discovery_url text,
    skip_nonce_check boolean DEFAULT false NOT NULL,
    cached_discovery jsonb,
    discovery_cached_at timestamp with time zone,
    authorization_url text,
    token_url text,
    userinfo_url text,
    jwks_uri text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT custom_oauth_providers_authorization_url_https CHECK (((authorization_url IS NULL) OR (authorization_url ~~ 'https://%'::text))),
    CONSTRAINT custom_oauth_providers_authorization_url_length CHECK (((authorization_url IS NULL) OR (char_length(authorization_url) <= 2048))),
    CONSTRAINT custom_oauth_providers_client_id_length CHECK (((char_length(client_id) >= 1) AND (char_length(client_id) <= 512))),
    CONSTRAINT custom_oauth_providers_discovery_url_length CHECK (((discovery_url IS NULL) OR (char_length(discovery_url) <= 2048))),
    CONSTRAINT custom_oauth_providers_identifier_format CHECK ((identifier ~ '^[a-z0-9][a-z0-9:-]{0,48}[a-z0-9]$'::text)),
    CONSTRAINT custom_oauth_providers_issuer_length CHECK (((issuer IS NULL) OR ((char_length(issuer) >= 1) AND (char_length(issuer) <= 2048)))),
    CONSTRAINT custom_oauth_providers_jwks_uri_https CHECK (((jwks_uri IS NULL) OR (jwks_uri ~~ 'https://%'::text))),
    CONSTRAINT custom_oauth_providers_jwks_uri_length CHECK (((jwks_uri IS NULL) OR (char_length(jwks_uri) <= 2048))),
    CONSTRAINT custom_oauth_providers_name_length CHECK (((char_length(name) >= 1) AND (char_length(name) <= 100))),
    CONSTRAINT custom_oauth_providers_oauth2_requires_endpoints CHECK (((provider_type <> 'oauth2'::text) OR ((authorization_url IS NOT NULL) AND (token_url IS NOT NULL) AND (userinfo_url IS NOT NULL)))),
    CONSTRAINT custom_oauth_providers_oidc_discovery_url_https CHECK (((provider_type <> 'oidc'::text) OR (discovery_url IS NULL) OR (discovery_url ~~ 'https://%'::text))),
    CONSTRAINT custom_oauth_providers_oidc_issuer_https CHECK (((provider_type <> 'oidc'::text) OR (issuer IS NULL) OR (issuer ~~ 'https://%'::text))),
    CONSTRAINT custom_oauth_providers_oidc_requires_issuer CHECK (((provider_type <> 'oidc'::text) OR (issuer IS NOT NULL))),
    CONSTRAINT custom_oauth_providers_provider_type_check CHECK ((provider_type = ANY (ARRAY['oauth2'::text, 'oidc'::text]))),
    CONSTRAINT custom_oauth_providers_token_url_https CHECK (((token_url IS NULL) OR (token_url ~~ 'https://%'::text))),
    CONSTRAINT custom_oauth_providers_token_url_length CHECK (((token_url IS NULL) OR (char_length(token_url) <= 2048))),
    CONSTRAINT custom_oauth_providers_userinfo_url_https CHECK (((userinfo_url IS NULL) OR (userinfo_url ~~ 'https://%'::text))),
    CONSTRAINT custom_oauth_providers_userinfo_url_length CHECK (((userinfo_url IS NULL) OR (char_length(userinfo_url) <= 2048)))
);


--
-- Name: flow_state; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.flow_state (
    id uuid NOT NULL,
    user_id uuid,
    auth_code text,
    code_challenge_method auth.code_challenge_method,
    code_challenge text,
    provider_type text NOT NULL,
    provider_access_token text,
    provider_refresh_token text,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    authentication_method text NOT NULL,
    auth_code_issued_at timestamp with time zone,
    invite_token text,
    referrer text,
    oauth_client_state_id uuid,
    linking_target_id uuid,
    email_optional boolean DEFAULT false NOT NULL
);


--
-- Name: TABLE flow_state; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON TABLE auth.flow_state IS 'Stores metadata for all OAuth/SSO login flows';


--
-- Name: identities; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.identities (
    provider_id text NOT NULL,
    user_id uuid NOT NULL,
    identity_data jsonb NOT NULL,
    provider text NOT NULL,
    last_sign_in_at timestamp with time zone,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    email text GENERATED ALWAYS AS (lower((identity_data ->> 'email'::text))) STORED,
    id uuid DEFAULT gen_random_uuid() NOT NULL
);


--
-- Name: TABLE identities; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON TABLE auth.identities IS 'Auth: Stores identities associated to a user.';


--
-- Name: COLUMN identities.email; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON COLUMN auth.identities.email IS 'Auth: Email is a generated column that references the optional email property in the identity_data';


--
-- Name: instances; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.instances (
    id uuid NOT NULL,
    uuid uuid,
    raw_base_config text,
    created_at timestamp with time zone,
    updated_at timestamp with time zone
);


--
-- Name: TABLE instances; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON TABLE auth.instances IS 'Auth: Manages users across multiple sites.';


--
-- Name: mfa_amr_claims; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.mfa_amr_claims (
    session_id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    authentication_method text NOT NULL,
    id uuid NOT NULL
);


--
-- Name: TABLE mfa_amr_claims; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON TABLE auth.mfa_amr_claims IS 'auth: stores authenticator method reference claims for multi factor authentication';


--
-- Name: mfa_challenges; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.mfa_challenges (
    id uuid NOT NULL,
    factor_id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    verified_at timestamp with time zone,
    ip_address inet NOT NULL,
    otp_code text,
    web_authn_session_data jsonb
);


--
-- Name: TABLE mfa_challenges; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON TABLE auth.mfa_challenges IS 'auth: stores metadata about challenge requests made';


--
-- Name: mfa_factors; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.mfa_factors (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    friendly_name text,
    factor_type auth.factor_type NOT NULL,
    status auth.factor_status NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    secret text,
    phone text,
    last_challenged_at timestamp with time zone,
    web_authn_credential jsonb,
    web_authn_aaguid uuid,
    last_webauthn_challenge_data jsonb
);


--
-- Name: TABLE mfa_factors; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON TABLE auth.mfa_factors IS 'auth: stores metadata about factors';


--
-- Name: COLUMN mfa_factors.last_webauthn_challenge_data; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON COLUMN auth.mfa_factors.last_webauthn_challenge_data IS 'Stores the latest WebAuthn challenge data including attestation/assertion for customer verification';


--
-- Name: oauth_authorizations; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.oauth_authorizations (
    id uuid NOT NULL,
    authorization_id text NOT NULL,
    client_id uuid NOT NULL,
    user_id uuid,
    redirect_uri text NOT NULL,
    scope text NOT NULL,
    state text,
    resource text,
    code_challenge text,
    code_challenge_method auth.code_challenge_method,
    response_type auth.oauth_response_type DEFAULT 'code'::auth.oauth_response_type NOT NULL,
    status auth.oauth_authorization_status DEFAULT 'pending'::auth.oauth_authorization_status NOT NULL,
    authorization_code text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone DEFAULT (now() + '00:03:00'::interval) NOT NULL,
    approved_at timestamp with time zone,
    nonce text,
    CONSTRAINT oauth_authorizations_authorization_code_length CHECK ((char_length(authorization_code) <= 255)),
    CONSTRAINT oauth_authorizations_code_challenge_length CHECK ((char_length(code_challenge) <= 128)),
    CONSTRAINT oauth_authorizations_expires_at_future CHECK ((expires_at > created_at)),
    CONSTRAINT oauth_authorizations_nonce_length CHECK ((char_length(nonce) <= 255)),
    CONSTRAINT oauth_authorizations_redirect_uri_length CHECK ((char_length(redirect_uri) <= 2048)),
    CONSTRAINT oauth_authorizations_resource_length CHECK ((char_length(resource) <= 2048)),
    CONSTRAINT oauth_authorizations_scope_length CHECK ((char_length(scope) <= 4096)),
    CONSTRAINT oauth_authorizations_state_length CHECK ((char_length(state) <= 4096))
);


--
-- Name: oauth_client_states; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.oauth_client_states (
    id uuid NOT NULL,
    provider_type text NOT NULL,
    code_verifier text,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: TABLE oauth_client_states; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON TABLE auth.oauth_client_states IS 'Stores OAuth states for third-party provider authentication flows where Supabase acts as the OAuth client.';


--
-- Name: oauth_clients; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.oauth_clients (
    id uuid NOT NULL,
    client_secret_hash text,
    registration_type auth.oauth_registration_type NOT NULL,
    redirect_uris text NOT NULL,
    grant_types text NOT NULL,
    client_name text,
    client_uri text,
    logo_uri text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    client_type auth.oauth_client_type DEFAULT 'confidential'::auth.oauth_client_type NOT NULL,
    token_endpoint_auth_method text NOT NULL,
    CONSTRAINT oauth_clients_client_name_length CHECK ((char_length(client_name) <= 1024)),
    CONSTRAINT oauth_clients_client_uri_length CHECK ((char_length(client_uri) <= 2048)),
    CONSTRAINT oauth_clients_logo_uri_length CHECK ((char_length(logo_uri) <= 2048)),
    CONSTRAINT oauth_clients_token_endpoint_auth_method_check CHECK ((token_endpoint_auth_method = ANY (ARRAY['client_secret_basic'::text, 'client_secret_post'::text, 'none'::text])))
);


--
-- Name: oauth_consents; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.oauth_consents (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    client_id uuid NOT NULL,
    scopes text NOT NULL,
    granted_at timestamp with time zone DEFAULT now() NOT NULL,
    revoked_at timestamp with time zone,
    CONSTRAINT oauth_consents_revoked_after_granted CHECK (((revoked_at IS NULL) OR (revoked_at >= granted_at))),
    CONSTRAINT oauth_consents_scopes_length CHECK ((char_length(scopes) <= 2048)),
    CONSTRAINT oauth_consents_scopes_not_empty CHECK ((char_length(TRIM(BOTH FROM scopes)) > 0))
);


--
-- Name: one_time_tokens; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.one_time_tokens (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    token_type auth.one_time_token_type NOT NULL,
    token_hash text NOT NULL,
    relates_to text NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    CONSTRAINT one_time_tokens_token_hash_check CHECK ((char_length(token_hash) > 0))
);


--
-- Name: refresh_tokens; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.refresh_tokens (
    instance_id uuid,
    id bigint NOT NULL,
    token character varying(255),
    user_id character varying(255),
    revoked boolean,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    parent character varying(255),
    session_id uuid
);


--
-- Name: TABLE refresh_tokens; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON TABLE auth.refresh_tokens IS 'Auth: Store of tokens used to refresh JWT tokens once they expire.';


--
-- Name: refresh_tokens_id_seq; Type: SEQUENCE; Schema: auth; Owner: -
--

CREATE SEQUENCE auth.refresh_tokens_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: refresh_tokens_id_seq; Type: SEQUENCE OWNED BY; Schema: auth; Owner: -
--

ALTER SEQUENCE auth.refresh_tokens_id_seq OWNED BY auth.refresh_tokens.id;


--
-- Name: saml_providers; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.saml_providers (
    id uuid NOT NULL,
    sso_provider_id uuid NOT NULL,
    entity_id text NOT NULL,
    metadata_xml text NOT NULL,
    metadata_url text,
    attribute_mapping jsonb,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    name_id_format text,
    CONSTRAINT "entity_id not empty" CHECK ((char_length(entity_id) > 0)),
    CONSTRAINT "metadata_url not empty" CHECK (((metadata_url = NULL::text) OR (char_length(metadata_url) > 0))),
    CONSTRAINT "metadata_xml not empty" CHECK ((char_length(metadata_xml) > 0))
);


--
-- Name: TABLE saml_providers; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON TABLE auth.saml_providers IS 'Auth: Manages SAML Identity Provider connections.';


--
-- Name: saml_relay_states; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.saml_relay_states (
    id uuid NOT NULL,
    sso_provider_id uuid NOT NULL,
    request_id text NOT NULL,
    for_email text,
    redirect_to text,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    flow_state_id uuid,
    CONSTRAINT "request_id not empty" CHECK ((char_length(request_id) > 0))
);


--
-- Name: TABLE saml_relay_states; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON TABLE auth.saml_relay_states IS 'Auth: Contains SAML Relay State information for each Service Provider initiated login.';


--
-- Name: schema_migrations; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.schema_migrations (
    version character varying(255) NOT NULL
);


--
-- Name: TABLE schema_migrations; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON TABLE auth.schema_migrations IS 'Auth: Manages updates to the auth system.';


--
-- Name: sessions; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.sessions (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    factor_id uuid,
    aal auth.aal_level,
    not_after timestamp with time zone,
    refreshed_at timestamp without time zone,
    user_agent text,
    ip inet,
    tag text,
    oauth_client_id uuid,
    refresh_token_hmac_key text,
    refresh_token_counter bigint,
    scopes text,
    CONSTRAINT sessions_scopes_length CHECK ((char_length(scopes) <= 4096))
);


--
-- Name: TABLE sessions; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON TABLE auth.sessions IS 'Auth: Stores session data associated to a user.';


--
-- Name: COLUMN sessions.not_after; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON COLUMN auth.sessions.not_after IS 'Auth: Not after is a nullable column that contains a timestamp after which the session should be regarded as expired.';


--
-- Name: COLUMN sessions.refresh_token_hmac_key; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON COLUMN auth.sessions.refresh_token_hmac_key IS 'Holds a HMAC-SHA256 key used to sign refresh tokens for this session.';


--
-- Name: COLUMN sessions.refresh_token_counter; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON COLUMN auth.sessions.refresh_token_counter IS 'Holds the ID (counter) of the last issued refresh token.';


--
-- Name: sso_domains; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.sso_domains (
    id uuid NOT NULL,
    sso_provider_id uuid NOT NULL,
    domain text NOT NULL,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    CONSTRAINT "domain not empty" CHECK ((char_length(domain) > 0))
);


--
-- Name: TABLE sso_domains; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON TABLE auth.sso_domains IS 'Auth: Manages SSO email address domain mapping to an SSO Identity Provider.';


--
-- Name: sso_providers; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.sso_providers (
    id uuid NOT NULL,
    resource_id text,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    disabled boolean,
    CONSTRAINT "resource_id not empty" CHECK (((resource_id = NULL::text) OR (char_length(resource_id) > 0)))
);


--
-- Name: TABLE sso_providers; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON TABLE auth.sso_providers IS 'Auth: Manages SSO identity provider information; see saml_providers for SAML.';


--
-- Name: COLUMN sso_providers.resource_id; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON COLUMN auth.sso_providers.resource_id IS 'Auth: Uniquely identifies a SSO provider according to a user-chosen resource ID (case insensitive), useful in infrastructure as code.';


--
-- Name: users; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.users (
    instance_id uuid,
    id uuid NOT NULL,
    aud character varying(255),
    role character varying(255),
    email character varying(255),
    encrypted_password character varying(255),
    email_confirmed_at timestamp with time zone,
    invited_at timestamp with time zone,
    confirmation_token character varying(255),
    confirmation_sent_at timestamp with time zone,
    recovery_token character varying(255),
    recovery_sent_at timestamp with time zone,
    email_change_token_new character varying(255),
    email_change character varying(255),
    email_change_sent_at timestamp with time zone,
    last_sign_in_at timestamp with time zone,
    raw_app_meta_data jsonb,
    raw_user_meta_data jsonb,
    is_super_admin boolean,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    phone text DEFAULT NULL::character varying,
    phone_confirmed_at timestamp with time zone,
    phone_change text DEFAULT ''::character varying,
    phone_change_token character varying(255) DEFAULT ''::character varying,
    phone_change_sent_at timestamp with time zone,
    confirmed_at timestamp with time zone GENERATED ALWAYS AS (LEAST(email_confirmed_at, phone_confirmed_at)) STORED,
    email_change_token_current character varying(255) DEFAULT ''::character varying,
    email_change_confirm_status smallint DEFAULT 0,
    banned_until timestamp with time zone,
    reauthentication_token character varying(255) DEFAULT ''::character varying,
    reauthentication_sent_at timestamp with time zone,
    is_sso_user boolean DEFAULT false NOT NULL,
    deleted_at timestamp with time zone,
    is_anonymous boolean DEFAULT false NOT NULL,
    CONSTRAINT users_email_change_confirm_status_check CHECK (((email_change_confirm_status >= 0) AND (email_change_confirm_status <= 2)))
);


--
-- Name: TABLE users; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON TABLE auth.users IS 'Auth: Stores user login data within a secure schema.';


--
-- Name: COLUMN users.is_sso_user; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON COLUMN auth.users.is_sso_user IS 'Auth: Set this column to true when the account comes from SSO. These accounts can have duplicate emails.';


--
-- Name: webauthn_challenges; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.webauthn_challenges (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    challenge_type text NOT NULL,
    session_data jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    CONSTRAINT webauthn_challenges_challenge_type_check CHECK ((challenge_type = ANY (ARRAY['signup'::text, 'registration'::text, 'authentication'::text])))
);


--
-- Name: webauthn_credentials; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.webauthn_credentials (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    credential_id bytea NOT NULL,
    public_key bytea NOT NULL,
    attestation_type text DEFAULT ''::text NOT NULL,
    aaguid uuid,
    sign_count bigint DEFAULT 0 NOT NULL,
    transports jsonb DEFAULT '[]'::jsonb NOT NULL,
    backup_eligible boolean DEFAULT false NOT NULL,
    backed_up boolean DEFAULT false NOT NULL,
    friendly_name text DEFAULT ''::text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    last_used_at timestamp with time zone
);


--
-- Name: audit_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_logs (
    id uuid DEFAULT extensions.uuid_generate_v4() NOT NULL,
    tenant_id uuid,
    user_id uuid,
    action character varying(50) NOT NULL,
    table_name character varying(100) NOT NULL,
    record_id character varying(100),
    old_values jsonb,
    new_values jsonb,
    ip_address character varying(45),
    user_agent text,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: brands; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.brands (
    id uuid DEFAULT extensions.uuid_generate_v4() NOT NULL,
    name character varying(100) NOT NULL,
    slug character varying(100) NOT NULL,
    logo_url text,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: carrier_status_mapping; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.carrier_status_mapping (
    id integer NOT NULL,
    provider character varying(50) NOT NULL,
    carrier_status character varying(100) NOT NULL,
    internal_status public.shipment_status NOT NULL
);


--
-- Name: carrier_status_mapping_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.carrier_status_mapping_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: carrier_status_mapping_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.carrier_status_mapping_id_seq OWNED BY public.carrier_status_mapping.id;


--
-- Name: cart_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.cart_items (
    id uuid DEFAULT extensions.uuid_generate_v4() NOT NULL,
    user_id uuid,
    product_id uuid,
    quantity integer DEFAULT 1 NOT NULL,
    size text,
    created_at timestamp with time zone DEFAULT now(),
    color text,
    variant_id uuid
);


--
-- Name: categories; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.categories (
    id uuid DEFAULT extensions.uuid_generate_v4() NOT NULL,
    name text NOT NULL,
    slug text NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    image_url text,
    video_url text,
    description text,
    is_active boolean DEFAULT true NOT NULL,
    sort_order integer DEFAULT 0 NOT NULL,
    meta_title text,
    meta_description text,
    show_on_home boolean DEFAULT false NOT NULL,
    updated_at timestamp with time zone DEFAULT now(),
    parent_id uuid
);


--
-- Name: coupon_categories; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.coupon_categories (
    coupon_id uuid NOT NULL,
    category_id uuid NOT NULL
);


--
-- Name: coupon_products; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.coupon_products (
    coupon_id uuid NOT NULL,
    product_id uuid NOT NULL
);


--
-- Name: coupon_segments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.coupon_segments (
    coupon_id uuid NOT NULL,
    segment character varying(20) NOT NULL,
    CONSTRAINT coupon_segments_segment_check CHECK (((segment)::text = ANY ((ARRAY['new_user'::character varying, 'vip'::character varying])::text[])))
);


--
-- Name: coupon_usages; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.coupon_usages (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    coupon_id uuid NOT NULL,
    order_id uuid NOT NULL,
    user_id uuid NOT NULL,
    discount_amount numeric(12,2),
    used_at timestamp with time zone DEFAULT now()
);


--
-- Name: coupons; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.coupons (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    code character varying(50) NOT NULL,
    description text,
    discount_type character varying(20) NOT NULL,
    discount_value numeric(12,2) DEFAULT 0,
    max_discount numeric(12,2),
    min_order_value numeric(12,2) DEFAULT 0,
    is_stackable boolean DEFAULT false,
    usage_limit integer,
    usage_per_user integer,
    starts_at timestamp with time zone,
    expires_at timestamp with time zone,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    is_first_order_only boolean DEFAULT false,
    max_usage_per_day integer,
    CONSTRAINT coupons_discount_type_check CHECK (((discount_type)::text = ANY ((ARRAY['percent'::character varying, 'fixed'::character varying, 'free_shipping'::character varying])::text[])))
);


--
-- Name: favorites; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.favorites (
    id uuid DEFAULT extensions.uuid_generate_v4() NOT NULL,
    user_id uuid NOT NULL,
    product_id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    channel text DEFAULT 'web'::text,
    source text DEFAULT 'organic'::text
);


--
-- Name: flash_sale_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.flash_sale_items (
    id uuid DEFAULT extensions.uuid_generate_v4() NOT NULL,
    flash_sale_id uuid,
    product_id uuid,
    variant_id uuid,
    promotional_price numeric(15,2) NOT NULL,
    quantity_limit integer NOT NULL,
    sold_quantity integer DEFAULT 0
);


--
-- Name: flash_sales; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.flash_sales (
    id uuid DEFAULT extensions.uuid_generate_v4() NOT NULL,
    name character varying(255) NOT NULL,
    starts_at timestamp with time zone NOT NULL,
    ends_at timestamp with time zone NOT NULL,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: inventory_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.inventory_logs (
    id uuid DEFAULT extensions.uuid_generate_v4() NOT NULL,
    product_id uuid,
    variant_id uuid,
    change_type character varying(50) NOT NULL,
    quantity_changed integer NOT NULL,
    stock_after integer NOT NULL,
    reference_id uuid,
    note text,
    created_by uuid,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: order_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.order_items (
    id uuid DEFAULT extensions.uuid_generate_v4() NOT NULL,
    order_id uuid,
    product_id uuid,
    quantity integer NOT NULL,
    unit_price numeric(12,0) NOT NULL,
    size text,
    variant_id uuid,
    product_name character varying(255) DEFAULT ''::character varying NOT NULL,
    variant_label character varying(255),
    price numeric
);


--
-- Name: orders; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.orders (
    id uuid DEFAULT extensions.uuid_generate_v4() NOT NULL,
    user_id uuid,
    total_amount numeric(14,0) DEFAULT 0 NOT NULL,
    shipping_address jsonb,
    status text DEFAULT 'pending'::text NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    payment_method text DEFAULT 'COD'::text,
    payment_status text DEFAULT 'pending'::text,
    transaction_id text,
    order_notes text,
    coupon_id uuid,
    discount_amount numeric(12,2) DEFAULT 0,
    is_return_requested boolean DEFAULT false,
    return_reason text,
    return_image_url text,
    refunded_amount numeric(12,2) DEFAULT 0,
    returned_at timestamp with time zone,
    shipping_fee numeric(12,2) DEFAULT 0,
    sales_channel text DEFAULT 'web'::text,
    source text DEFAULT 'web'::text,
    code text,
    customer_name text,
    customer_phone text,
    CONSTRAINT orders_status_check CHECK ((status = ANY (ARRAY['pending'::text, 'confirmed'::text, 'packed'::text, 'shipped'::text, 'shipping'::text, 'delivered'::text, 'completed'::text, 'cancelled'::text, 'failed'::text, 'returned'::text])))
);


--
-- Name: payments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.payments (
    id uuid DEFAULT extensions.uuid_generate_v4() NOT NULL,
    order_id uuid,
    provider character varying(50) NOT NULL,
    transaction_id character varying(255),
    amount numeric(15,2) NOT NULL,
    status character varying(50) DEFAULT 'pending'::character varying NOT NULL,
    raw_response jsonb,
    paid_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: permission_groups; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.permission_groups (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    sort_order integer DEFAULT 0
);


--
-- Name: permission_groups_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.permission_groups_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: permission_groups_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.permission_groups_id_seq OWNED BY public.permission_groups.id;


--
-- Name: permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.permissions (
    id integer NOT NULL,
    group_id integer,
    code character varying(100) NOT NULL,
    display_name character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.permissions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: permissions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.permissions_id_seq OWNED BY public.permissions.id;


--
-- Name: product_analytics; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.product_analytics (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    product_id uuid,
    channel text NOT NULL,
    source text DEFAULT 'organic'::text,
    views integer DEFAULT 0,
    add_to_carts integer DEFAULT 0,
    sold integer DEFAULT 0,
    wishlist_count integer DEFAULT 0,
    revenue numeric DEFAULT 0,
    report_date date DEFAULT CURRENT_DATE,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT chk_channel CHECK ((channel = ANY (ARRAY['web'::text, 'pos'::text, 'tiktok'::text, 'shopee'::text, 'facebook'::text, 'instagram'::text])))
);


--
-- Name: product_images; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.product_images (
    id uuid DEFAULT extensions.uuid_generate_v4() NOT NULL,
    product_id uuid NOT NULL,
    url text NOT NULL,
    is_primary boolean DEFAULT false,
    sort_order integer DEFAULT 0 NOT NULL
);


--
-- Name: product_reviews; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.product_reviews (
    id uuid DEFAULT extensions.uuid_generate_v4() NOT NULL,
    product_id uuid,
    user_id uuid,
    order_id uuid,
    rating integer,
    comment text,
    images text[] DEFAULT '{}'::text[],
    reply_comment text,
    is_hidden boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT product_reviews_rating_check CHECK (((rating >= 1) AND (rating <= 5)))
);


--
-- Name: product_variants; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.product_variants (
    id uuid DEFAULT extensions.uuid_generate_v4() NOT NULL,
    product_id uuid NOT NULL,
    size text NOT NULL,
    color_name text NOT NULL,
    color_hex text,
    sku text,
    price_override numeric,
    stock integer DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: products; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.products (
    id uuid DEFAULT extensions.uuid_generate_v4() NOT NULL,
    name text NOT NULL,
    description text,
    price numeric(12,0) DEFAULT 0 NOT NULL,
    stock integer DEFAULT 0 NOT NULL,
    category_id uuid,
    thumbnail_url text,
    is_featured boolean DEFAULT false,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    rating numeric DEFAULT 4.5,
    sold_count integer DEFAULT 0,
    discount integer DEFAULT 0,
    slug text NOT NULL,
    meta_title text,
    meta_description text,
    brand text DEFAULT 'GUA Maison'::text,
    gender text,
    tags text[],
    deleted_at timestamp with time zone,
    created_by uuid,
    textsearchable_index_col tsvector GENERATED ALWAYS AS (to_tsvector('simple'::regconfig, ((COALESCE(name, ''::text) || ' '::text) || COALESCE(description, ''::text)))) STORED,
    brand_id uuid,
    attributes jsonb DEFAULT '{}'::jsonb
);


--
-- Name: return_requests; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.return_requests (
    id uuid DEFAULT extensions.uuid_generate_v4() NOT NULL,
    order_id uuid NOT NULL,
    user_id uuid NOT NULL,
    reason text NOT NULL,
    image_url text NOT NULL,
    requested_at timestamp with time zone DEFAULT now() NOT NULL,
    status text DEFAULT 'pending'::text NOT NULL,
    reviewed_by uuid,
    reviewed_at timestamp with time zone,
    admin_note text,
    refunded_at timestamp with time zone,
    refund_amount numeric(12,2),
    CONSTRAINT return_requests_status_check CHECK ((status = ANY (ARRAY['pending'::text, 'approved'::text, 'rejected'::text, 'refunded'::text])))
);


--
-- Name: role_permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.role_permissions (
    role_id integer NOT NULL,
    permission_id integer NOT NULL
);


--
-- Name: roles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.roles (
    id integer NOT NULL,
    tenant_id uuid,
    parent_id integer,
    name character varying(100) NOT NULL,
    description text,
    is_active boolean DEFAULT true,
    deleted_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: roles_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.roles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: roles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.roles_id_seq OWNED BY public.roles.id;


--
-- Name: shipment_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.shipment_events (
    id uuid DEFAULT extensions.uuid_generate_v4() NOT NULL,
    shipment_id uuid,
    status public.shipment_status NOT NULL,
    description text,
    location character varying(255),
    raw_data jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: shipments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.shipments (
    id uuid DEFAULT extensions.uuid_generate_v4() NOT NULL,
    order_id uuid,
    provider character varying(50) DEFAULT 'mock'::character varying NOT NULL,
    tracking_code character varying(100),
    shipping_fee numeric(12,2) DEFAULT 0,
    actual_shipping_fee numeric(12,2) DEFAULT 0,
    cod_amount numeric(12,2) DEFAULT 0,
    package_index integer DEFAULT 1,
    weight_g integer DEFAULT 0,
    dimensions_json jsonb DEFAULT '{"h": 0, "l": 0, "w": 0}'::jsonb,
    recipient_name character varying(255) NOT NULL,
    recipient_phone character varying(50) NOT NULL,
    recipient_address text NOT NULL,
    recipient_ward_code character varying(20),
    recipient_district_id integer,
    recipient_province_id integer,
    status public.shipment_status DEFAULT 'pending'::public.shipment_status,
    delayed boolean DEFAULT false,
    expected_delivery_at timestamp with time zone,
    shipped_at timestamp with time zone,
    delivered_at timestamp with time zone,
    raw_response jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    delivery_attempts integer DEFAULT 0,
    failed_reason text
);


--
-- Name: shipping_configs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.shipping_configs (
    id integer DEFAULT 1 NOT NULL,
    freeship_threshold numeric(12,2) DEFAULT 1500000,
    hcm_fee numeric(12,2) DEFAULT 25000,
    hn_fee numeric(12,2) DEFAULT 35000,
    default_fee numeric(12,2) DEFAULT 45000,
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: shipping_providers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.shipping_providers (
    id text NOT NULL,
    name text NOT NULL,
    description text,
    is_active boolean DEFAULT false,
    config jsonb DEFAULT '{}'::jsonb,
    icon text,
    sort_order integer DEFAULT 0,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: system_settings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.system_settings (
    id integer DEFAULT 1 NOT NULL,
    general jsonb DEFAULT '{}'::jsonb,
    storefront jsonb DEFAULT '{}'::jsonb,
    integrations jsonb DEFAULT '{}'::jsonb,
    updated_at timestamp with time zone DEFAULT now(),
    shipping_rules jsonb DEFAULT '[]'::jsonb
);


--
-- Name: tenants; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tenants (
    id uuid DEFAULT extensions.uuid_generate_v4() NOT NULL,
    name character varying(255) NOT NULL,
    domain character varying(255),
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: user_addresses; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_addresses (
    id uuid DEFAULT extensions.uuid_generate_v4() NOT NULL,
    user_id uuid NOT NULL,
    full_name text NOT NULL,
    phone text NOT NULL,
    address_line text NOT NULL,
    is_default boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now(),
    province text,
    district text,
    ward text,
    note text
);


--
-- Name: user_permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_permissions (
    user_id uuid NOT NULL,
    permission_id integer NOT NULL,
    is_granted boolean DEFAULT true
);


--
-- Name: user_roles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_roles (
    user_id uuid NOT NULL,
    role_id integer NOT NULL,
    tenant_id uuid
);


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id uuid DEFAULT extensions.uuid_generate_v4() NOT NULL,
    email text NOT NULL,
    password_hash text NOT NULL,
    full_name text NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    phone text,
    is_vip boolean DEFAULT false,
    role text DEFAULT 'customer'::text
);


--
-- Name: webhook_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.webhook_logs (
    id uuid DEFAULT extensions.uuid_generate_v4() NOT NULL,
    provider character varying(50) NOT NULL,
    event_type character varying(100),
    payload jsonb NOT NULL,
    status_code integer,
    error_message text,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: messages; Type: TABLE; Schema: realtime; Owner: -
--

CREATE TABLE realtime.messages (
    topic text NOT NULL,
    extension text NOT NULL,
    payload jsonb,
    event text,
    private boolean DEFAULT false,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    inserted_at timestamp without time zone DEFAULT now() NOT NULL,
    id uuid DEFAULT gen_random_uuid() NOT NULL
)
PARTITION BY RANGE (inserted_at);


--
-- Name: schema_migrations; Type: TABLE; Schema: realtime; Owner: -
--

CREATE TABLE realtime.schema_migrations (
    version bigint NOT NULL,
    inserted_at timestamp(0) without time zone
);


--
-- Name: subscription; Type: TABLE; Schema: realtime; Owner: -
--

CREATE TABLE realtime.subscription (
    id bigint NOT NULL,
    subscription_id uuid NOT NULL,
    entity regclass NOT NULL,
    filters realtime.user_defined_filter[] DEFAULT '{}'::realtime.user_defined_filter[] NOT NULL,
    claims jsonb NOT NULL,
    claims_role regrole GENERATED ALWAYS AS (realtime.to_regrole((claims ->> 'role'::text))) STORED NOT NULL,
    created_at timestamp without time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    action_filter text DEFAULT '*'::text,
    CONSTRAINT subscription_action_filter_check CHECK ((action_filter = ANY (ARRAY['*'::text, 'INSERT'::text, 'UPDATE'::text, 'DELETE'::text])))
);


--
-- Name: subscription_id_seq; Type: SEQUENCE; Schema: realtime; Owner: -
--

ALTER TABLE realtime.subscription ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME realtime.subscription_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: buckets; Type: TABLE; Schema: storage; Owner: -
--

CREATE TABLE storage.buckets (
    id text NOT NULL,
    name text NOT NULL,
    owner uuid,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    public boolean DEFAULT false,
    avif_autodetection boolean DEFAULT false,
    file_size_limit bigint,
    allowed_mime_types text[],
    owner_id text,
    type storage.buckettype DEFAULT 'STANDARD'::storage.buckettype NOT NULL
);


--
-- Name: COLUMN buckets.owner; Type: COMMENT; Schema: storage; Owner: -
--

COMMENT ON COLUMN storage.buckets.owner IS 'Field is deprecated, use owner_id instead';


--
-- Name: buckets_analytics; Type: TABLE; Schema: storage; Owner: -
--

CREATE TABLE storage.buckets_analytics (
    name text NOT NULL,
    type storage.buckettype DEFAULT 'ANALYTICS'::storage.buckettype NOT NULL,
    format text DEFAULT 'ICEBERG'::text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    deleted_at timestamp with time zone
);


--
-- Name: buckets_vectors; Type: TABLE; Schema: storage; Owner: -
--

CREATE TABLE storage.buckets_vectors (
    id text NOT NULL,
    type storage.buckettype DEFAULT 'VECTOR'::storage.buckettype NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: migrations; Type: TABLE; Schema: storage; Owner: -
--

CREATE TABLE storage.migrations (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    hash character varying(40) NOT NULL,
    executed_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: objects; Type: TABLE; Schema: storage; Owner: -
--

CREATE TABLE storage.objects (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    bucket_id text,
    name text,
    owner uuid,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    last_accessed_at timestamp with time zone DEFAULT now(),
    metadata jsonb,
    path_tokens text[] GENERATED ALWAYS AS (string_to_array(name, '/'::text)) STORED,
    version text,
    owner_id text,
    user_metadata jsonb
);


--
-- Name: COLUMN objects.owner; Type: COMMENT; Schema: storage; Owner: -
--

COMMENT ON COLUMN storage.objects.owner IS 'Field is deprecated, use owner_id instead';


--
-- Name: s3_multipart_uploads; Type: TABLE; Schema: storage; Owner: -
--

CREATE TABLE storage.s3_multipart_uploads (
    id text NOT NULL,
    in_progress_size bigint DEFAULT 0 NOT NULL,
    upload_signature text NOT NULL,
    bucket_id text NOT NULL,
    key text NOT NULL COLLATE pg_catalog."C",
    version text NOT NULL,
    owner_id text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    user_metadata jsonb,
    metadata jsonb
);


--
-- Name: s3_multipart_uploads_parts; Type: TABLE; Schema: storage; Owner: -
--

CREATE TABLE storage.s3_multipart_uploads_parts (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    upload_id text NOT NULL,
    size bigint DEFAULT 0 NOT NULL,
    part_number integer NOT NULL,
    bucket_id text NOT NULL,
    key text NOT NULL COLLATE pg_catalog."C",
    etag text NOT NULL,
    owner_id text,
    version text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: vector_indexes; Type: TABLE; Schema: storage; Owner: -
--

CREATE TABLE storage.vector_indexes (
    id text DEFAULT gen_random_uuid() NOT NULL,
    name text NOT NULL COLLATE pg_catalog."C",
    bucket_id text NOT NULL,
    data_type text NOT NULL,
    dimension integer NOT NULL,
    distance_metric text NOT NULL,
    metadata_configuration jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: refresh_tokens id; Type: DEFAULT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.refresh_tokens ALTER COLUMN id SET DEFAULT nextval('auth.refresh_tokens_id_seq'::regclass);


--
-- Name: carrier_status_mapping id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.carrier_status_mapping ALTER COLUMN id SET DEFAULT nextval('public.carrier_status_mapping_id_seq'::regclass);


--
-- Name: permission_groups id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.permission_groups ALTER COLUMN id SET DEFAULT nextval('public.permission_groups_id_seq'::regclass);


--
-- Name: permissions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.permissions ALTER COLUMN id SET DEFAULT nextval('public.permissions_id_seq'::regclass);


--
-- Name: roles id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.roles ALTER COLUMN id SET DEFAULT nextval('public.roles_id_seq'::regclass);


--
-- Data for Name: audit_log_entries; Type: TABLE DATA; Schema: auth; Owner: -
--

COPY auth.audit_log_entries (instance_id, id, payload, created_at, ip_address) FROM stdin;
\.


--
-- Data for Name: custom_oauth_providers; Type: TABLE DATA; Schema: auth; Owner: -
--

COPY auth.custom_oauth_providers (id, provider_type, identifier, name, client_id, client_secret, acceptable_client_ids, scopes, pkce_enabled, attribute_mapping, authorization_params, enabled, email_optional, issuer, discovery_url, skip_nonce_check, cached_discovery, discovery_cached_at, authorization_url, token_url, userinfo_url, jwks_uri, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: flow_state; Type: TABLE DATA; Schema: auth; Owner: -
--

COPY auth.flow_state (id, user_id, auth_code, code_challenge_method, code_challenge, provider_type, provider_access_token, provider_refresh_token, created_at, updated_at, authentication_method, auth_code_issued_at, invite_token, referrer, oauth_client_state_id, linking_target_id, email_optional) FROM stdin;
\.


--
-- Data for Name: identities; Type: TABLE DATA; Schema: auth; Owner: -
--

COPY auth.identities (provider_id, user_id, identity_data, provider, last_sign_in_at, created_at, updated_at, id) FROM stdin;
\.


--
-- Data for Name: instances; Type: TABLE DATA; Schema: auth; Owner: -
--

COPY auth.instances (id, uuid, raw_base_config, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: mfa_amr_claims; Type: TABLE DATA; Schema: auth; Owner: -
--

COPY auth.mfa_amr_claims (session_id, created_at, updated_at, authentication_method, id) FROM stdin;
\.


--
-- Data for Name: mfa_challenges; Type: TABLE DATA; Schema: auth; Owner: -
--

COPY auth.mfa_challenges (id, factor_id, created_at, verified_at, ip_address, otp_code, web_authn_session_data) FROM stdin;
\.


--
-- Data for Name: mfa_factors; Type: TABLE DATA; Schema: auth; Owner: -
--

COPY auth.mfa_factors (id, user_id, friendly_name, factor_type, status, created_at, updated_at, secret, phone, last_challenged_at, web_authn_credential, web_authn_aaguid, last_webauthn_challenge_data) FROM stdin;
\.


--
-- Data for Name: oauth_authorizations; Type: TABLE DATA; Schema: auth; Owner: -
--

COPY auth.oauth_authorizations (id, authorization_id, client_id, user_id, redirect_uri, scope, state, resource, code_challenge, code_challenge_method, response_type, status, authorization_code, created_at, expires_at, approved_at, nonce) FROM stdin;
\.


--
-- Data for Name: oauth_client_states; Type: TABLE DATA; Schema: auth; Owner: -
--

COPY auth.oauth_client_states (id, provider_type, code_verifier, created_at) FROM stdin;
\.


--
-- Data for Name: oauth_clients; Type: TABLE DATA; Schema: auth; Owner: -
--

COPY auth.oauth_clients (id, client_secret_hash, registration_type, redirect_uris, grant_types, client_name, client_uri, logo_uri, created_at, updated_at, deleted_at, client_type, token_endpoint_auth_method) FROM stdin;
\.


--
-- Data for Name: oauth_consents; Type: TABLE DATA; Schema: auth; Owner: -
--

COPY auth.oauth_consents (id, user_id, client_id, scopes, granted_at, revoked_at) FROM stdin;
\.


--
-- Data for Name: one_time_tokens; Type: TABLE DATA; Schema: auth; Owner: -
--

COPY auth.one_time_tokens (id, user_id, token_type, token_hash, relates_to, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: refresh_tokens; Type: TABLE DATA; Schema: auth; Owner: -
--

COPY auth.refresh_tokens (instance_id, id, token, user_id, revoked, created_at, updated_at, parent, session_id) FROM stdin;
\.


--
-- Data for Name: saml_providers; Type: TABLE DATA; Schema: auth; Owner: -
--

COPY auth.saml_providers (id, sso_provider_id, entity_id, metadata_xml, metadata_url, attribute_mapping, created_at, updated_at, name_id_format) FROM stdin;
\.


--
-- Data for Name: saml_relay_states; Type: TABLE DATA; Schema: auth; Owner: -
--

COPY auth.saml_relay_states (id, sso_provider_id, request_id, for_email, redirect_to, created_at, updated_at, flow_state_id) FROM stdin;
\.


--
-- Data for Name: schema_migrations; Type: TABLE DATA; Schema: auth; Owner: -
--

COPY auth.schema_migrations (version) FROM stdin;
20171026211738
20171026211808
20171026211834
20180103212743
20180108183307
20180119214651
20180125194653
00
20210710035447
20210722035447
20210730183235
20210909172000
20210927181326
20211122151130
20211124214934
20211202183645
20220114185221
20220114185340
20220224000811
20220323170000
20220429102000
20220531120530
20220614074223
20220811173540
20221003041349
20221003041400
20221011041400
20221020193600
20221021073300
20221021082433
20221027105023
20221114143122
20221114143410
20221125140132
20221208132122
20221215195500
20221215195800
20221215195900
20230116124310
20230116124412
20230131181311
20230322519590
20230402418590
20230411005111
20230508135423
20230523124323
20230818113222
20230914180801
20231027141322
20231114161723
20231117164230
20240115144230
20240214120130
20240306115329
20240314092811
20240427152123
20240612123726
20240729123726
20240802193726
20240806073726
20241009103726
20250717082212
20250731150234
20250804100000
20250901200500
20250903112500
20250904133000
20250925093508
20251007112900
20251104100000
20251111201300
20251201000000
20260115000000
20260121000000
20260219120000
20260302000000
\.


--
-- Data for Name: sessions; Type: TABLE DATA; Schema: auth; Owner: -
--

COPY auth.sessions (id, user_id, created_at, updated_at, factor_id, aal, not_after, refreshed_at, user_agent, ip, tag, oauth_client_id, refresh_token_hmac_key, refresh_token_counter, scopes) FROM stdin;
\.


--
-- Data for Name: sso_domains; Type: TABLE DATA; Schema: auth; Owner: -
--

COPY auth.sso_domains (id, sso_provider_id, domain, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: sso_providers; Type: TABLE DATA; Schema: auth; Owner: -
--

COPY auth.sso_providers (id, resource_id, created_at, updated_at, disabled) FROM stdin;
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: auth; Owner: -
--

COPY auth.users (instance_id, id, aud, role, email, encrypted_password, email_confirmed_at, invited_at, confirmation_token, confirmation_sent_at, recovery_token, recovery_sent_at, email_change_token_new, email_change, email_change_sent_at, last_sign_in_at, raw_app_meta_data, raw_user_meta_data, is_super_admin, created_at, updated_at, phone, phone_confirmed_at, phone_change, phone_change_token, phone_change_sent_at, email_change_token_current, email_change_confirm_status, banned_until, reauthentication_token, reauthentication_sent_at, is_sso_user, deleted_at, is_anonymous) FROM stdin;
\.


--
-- Data for Name: webauthn_challenges; Type: TABLE DATA; Schema: auth; Owner: -
--

COPY auth.webauthn_challenges (id, user_id, challenge_type, session_data, created_at, expires_at) FROM stdin;
\.


--
-- Data for Name: webauthn_credentials; Type: TABLE DATA; Schema: auth; Owner: -
--

COPY auth.webauthn_credentials (id, user_id, credential_id, public_key, attestation_type, aaguid, sign_count, transports, backup_eligible, backed_up, friendly_name, created_at, updated_at, last_used_at) FROM stdin;
\.


--
-- Data for Name: audit_logs; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.audit_logs (id, tenant_id, user_id, action, table_name, record_id, old_values, new_values, ip_address, user_agent, created_at) FROM stdin;
\.


--
-- Data for Name: brands; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.brands (id, name, slug, logo_url, created_at) FROM stdin;
\.


--
-- Data for Name: carrier_status_mapping; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.carrier_status_mapping (id, provider, carrier_status, internal_status) FROM stdin;
\.


--
-- Data for Name: cart_items; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.cart_items (id, user_id, product_id, quantity, size, created_at, color, variant_id) FROM stdin;
39c5069d-b93d-4cce-93e0-6b10aedbdd2f	54bcef72-5d6d-4e21-bee1-e54e6592de9f	49f33164-1b39-462d-809e-9912bb9eec88	2	\N	2026-05-08 02:55:46.195868+00	\N	cb7bc29f-68d0-45bf-ba7e-b259eef8111d
c6b966cd-4a0d-4720-b97e-3b775d4e24df	1aa70cbe-823c-4877-9344-cf1fdefced30	1cf9e9ff-f61a-472f-9d64-f8350dc55a85	1	\N	2026-05-08 13:04:17.460256+00	\N	cf0ee1cd-ebfc-4447-872f-cdc1b41ba6b8
\.


--
-- Data for Name: categories; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.categories (id, name, slug, created_at, image_url, video_url, description, is_active, sort_order, meta_title, meta_description, show_on_home, updated_at, parent_id) FROM stdin;
18ce9ffd-9078-4174-a8a1-11c1a3d217b9	unisex	unisex	2026-04-22 00:53:35.622246+00	\N	\N	\N	t	0	\N	\N	f	2026-05-07 13:30:12.078194+00	\N
baf050ba-30a9-4c39-8a05-b64a2f59bbd6	Bộ Sưu Tập Mùa Hè	bo-suu-tap-mua-he	2026-05-07 06:57:03.222797+00	https://i.pinimg.com/736x/40/1f/9d/401f9d6ed3d5267194e459028f40413a.jpg	\N	None	t	0	\N	\N	t	2026-05-07 14:06:36.958838+00	\N
03b1c590-5a48-42ad-9cdf-312aa80baca7	MONDAY	monday	2026-05-07 09:19:37.246068+00	https://i.pinimg.com/736x/98/34/51/983451d630e91e11cbc455b16486339f.jpg	\N	None	t	0	\N	\N	t	2026-05-07 14:06:44.859964+00	\N
36f08100-d8ea-42a0-8c4e-c9f20b45ed26	Sale	sale	2026-04-21 09:54:31.34256+00	https://i.pinimg.com/1200x/34/87/29/34872971b5cff3678fd2d69c7643d2fe.jpg	\N	None	t	0	\N	\N	t	2026-05-07 14:06:52.568017+00	\N
3a896646-c830-458c-9782-9746ea277c4f	SHOT	shot	2026-05-07 09:29:26.976472+00	https://i.pinimg.com/736x/ee/a9/31/eea93137029e450ab4960319ef4a11c7.jpg	\N	None	t	0	\N	\N	t	2026-05-07 14:06:59.649828+00	\N
\.


--
-- Data for Name: coupon_categories; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.coupon_categories (coupon_id, category_id) FROM stdin;
\.


--
-- Data for Name: coupon_products; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.coupon_products (coupon_id, product_id) FROM stdin;
\.


--
-- Data for Name: coupon_segments; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.coupon_segments (coupon_id, segment) FROM stdin;
\.


--
-- Data for Name: coupon_usages; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.coupon_usages (id, coupon_id, order_id, user_id, discount_amount, used_at) FROM stdin;
\.


--
-- Data for Name: coupons; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.coupons (id, code, description, discount_type, discount_value, max_discount, min_order_value, is_stackable, usage_limit, usage_per_user, starts_at, expires_at, is_active, created_at, updated_at, is_first_order_only, max_usage_per_day) FROM stdin;
81e7f540-cdb5-448b-a341-d52f0fbea762	QUOCTELAODONG		percent	20.00	200000.00	1000000.00	f	\N	\N	\N	2026-05-26 15:20:00+00	t	2026-05-02 08:20:44.530585+00	2026-05-02 08:20:44.530585+00	f	\N
432d3deb-a06f-4583-9cc4-7882e94464c0	NGAYHOI55		fixed	50000.00	\N	798000.00	f	\N	1	2026-05-05 09:42:00+00	2026-05-07 09:42:00+00	t	2026-05-06 02:42:20.652561+00	2026-05-06 02:42:20.652561+00	f	\N
51b5e490-6edd-4325-8768-81e988008b28	MUAHE		percent	10.00	50000.00	100000.00	f	\N	1	2026-05-06 14:13:00+00	2026-05-07 03:13:00+00	t	2026-05-06 07:13:48.926552+00	2026-05-06 07:13:48.926552+00	f	\N
\.


--
-- Data for Name: favorites; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.favorites (id, user_id, product_id, created_at, channel, source) FROM stdin;
9957f3b4-f0ac-489f-a1f2-7a10cc5937ab	99db0bbc-628f-49e7-83f7-d5e41cddc33c	11111111-1111-1111-1111-111111111111	2026-05-03 01:49:42.810801+00	web	organic
01b6589d-146d-4950-99d7-f7d6be2b939e	99db0bbc-628f-49e7-83f7-d5e41cddc33c	55555555-5555-5555-5555-555555555555	2026-05-03 02:21:20.484693+00	web	organic
17435112-375f-46a1-b727-4b97b1f10073	30983a82-b6b8-4615-b6dd-ee97476851fd	11111111-1111-1111-1111-111111111111	2026-05-03 02:37:26.512562+00	web	organic
44835500-9deb-4c3f-b787-b1ce30a2b31b	1aa70cbe-823c-4877-9344-cf1fdefced30	11111111-1111-1111-1111-111111111111	2026-05-05 13:53:20.768312+00	web	organic
582aa2c0-19f1-4a14-91e7-2437e1285228	1aa70cbe-823c-4877-9344-cf1fdefced30	f8e05505-a89b-4188-a173-90b4c6db1f09	2026-05-07 03:11:38.665931+00	web	organic
f0a958aa-866f-4b33-b196-66d1a03d18d4	54bcef72-5d6d-4e21-bee1-e54e6592de9f	00237cc4-4c67-4074-846c-8724b36144c5	2026-05-07 06:52:05.039557+00	web	organic
8e80b637-ae8b-4732-888e-c37a89626e69	1aa70cbe-823c-4877-9344-cf1fdefced30	1cf9e9ff-f61a-472f-9d64-f8350dc55a85	2026-05-08 01:40:46.462124+00	web	organic
831134c4-fcac-4572-8199-ae8fbe8bb394	1aa70cbe-823c-4877-9344-cf1fdefced30	49f33164-1b39-462d-809e-9912bb9eec88	2026-05-08 02:06:06.944535+00	web	organic
27627f2c-9a5d-44bd-806b-761ea832aaeb	54bcef72-5d6d-4e21-bee1-e54e6592de9f	49f33164-1b39-462d-809e-9912bb9eec88	2026-05-08 03:55:33.021769+00	web	organic
747ff9ba-3fff-4085-92d1-084d68716a51	5a318635-d758-4b20-99ac-b79d097f0072	1cf9e9ff-f61a-472f-9d64-f8350dc55a85	2026-05-08 13:27:15.707176+00	web	organic
55afd31a-169e-466f-a64f-80a3ae4d98b8	5a318635-d758-4b20-99ac-b79d097f0072	9943a8c0-dc51-4a49-918c-d56aa08d5f81	2026-05-08 13:27:23.351851+00	web	organic
\.


--
-- Data for Name: flash_sale_items; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.flash_sale_items (id, flash_sale_id, product_id, variant_id, promotional_price, quantity_limit, sold_quantity) FROM stdin;
\.


--
-- Data for Name: flash_sales; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.flash_sales (id, name, starts_at, ends_at, is_active, created_at) FROM stdin;
\.


--
-- Data for Name: inventory_logs; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.inventory_logs (id, product_id, variant_id, change_type, quantity_changed, stock_after, reference_id, note, created_by, created_at) FROM stdin;
\.


--
-- Data for Name: order_items; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.order_items (id, order_id, product_id, quantity, unit_price, size, variant_id, product_name, variant_label, price) FROM stdin;
d4ca64b8-fe26-4bf5-a59c-15a2edb16274	64b64cd1-94b4-4660-b7cd-0cfe3f8d92a3	55555555-5555-5555-5555-555555555555	4	420000	\N	3964fa68-4bf1-4846-aae7-01fed71cdcb6		\N	\N
fbe8eb37-abaf-4000-8fd1-cf70b34d39c5	74c72a61-ef43-4076-8a0c-7ac850431171	33333333-3333-3333-3333-333333333333	1	450000	\N	ef953bc6-19f5-429a-b63b-ccb72df6260e		\N	\N
42f83b05-625f-494c-850b-0c3bfbb1240c	c701c201-3df9-4144-9381-79fa0ff6ed58	33333333-3333-3333-3333-333333333333	1	450000	\N	0a5607b4-effb-4762-aeee-3b23390e3ac7		\N	\N
65903790-05c6-4fc8-a988-0ef160a742fa	b7105c04-40df-4012-b5db-ec309c6865f5	44444444-4444-4444-4444-444444444444	2	890000	\N	d57f2203-4680-431f-a2ad-b8941112dfed		\N	\N
12771a5b-f982-484a-bdbe-41556df84e7f	552046cb-2fc6-4571-bab9-dc60926c50a8	11111111-1111-1111-1111-111111111111	1	350000	\N	6260ec38-ef08-49d0-9c95-fee8c821ad84		\N	\N
9f68e81e-0865-44d6-97ec-02c5ba67ea7b	df33294a-185c-46b4-ac95-0c9f9e3f2de0	55555555-5555-5555-5555-555555555555	2	420000	\N	6e8a6232-1e32-4a75-9884-11b5094e86bf		\N	\N
5c86c07e-4232-4920-9c94-7bd1512948c2	b758fa17-9d31-4ce1-8a13-809e25bca07f	55555555-5555-5555-5555-555555555555	2	420000	\N	6e8a6232-1e32-4a75-9884-11b5094e86bf		\N	\N
3586499f-ae7c-41fc-90b6-c066b1f68471	25a25b81-de72-4831-a3bb-0c00e95c0dbf	11111111-1111-1111-1111-111111111111	3	350000	\N	cc035689-aa92-402a-a93e-87791640bd81		\N	\N
a841b56d-02c4-4b45-b916-9abca4631d54	9952a72a-a679-4af8-aaf1-dac61e9b52b9	11111111-1111-1111-1111-111111111111	3	350000	\N	cc035689-aa92-402a-a93e-87791640bd81		\N	\N
e6abdd79-46a0-4a6c-ba18-1bab3bd3ee7e	9ee3b05a-39e9-4c28-a759-f7b311f8b8b8	44444444-4444-4444-4444-444444444444	1	890000	\N	347fb8ea-d7c9-42b7-b873-02a819a28168		\N	\N
f1f20371-e068-4566-8d89-1099f20e8f67	bd3885ae-7c17-4d00-8a40-fc99019c3343	44444444-4444-4444-4444-444444444444	1	890000	\N	347fb8ea-d7c9-42b7-b873-02a819a28168		\N	\N
5f15de71-8cd4-475c-b8f9-209b08b41fbb	661a642d-2c64-468a-ae02-5c600919748d	44444444-4444-4444-4444-444444444444	1	890000	\N	347fb8ea-d7c9-42b7-b873-02a819a28168		\N	\N
7f19623e-7a53-4136-b485-181a15dfcb0d	82afa8b2-c274-4eec-8d91-3c691318f59b	44444444-4444-4444-4444-444444444444	1	890000	\N	347fb8ea-d7c9-42b7-b873-02a819a28168		\N	\N
89f5c19f-5887-402e-a282-4cbd1d964093	8b03b65f-1d28-4c0f-b975-c748546f037a	44444444-4444-4444-4444-444444444444	1	890000	\N	347fb8ea-d7c9-42b7-b873-02a819a28168		\N	\N
82e62419-1430-475e-8415-52a492f00be3	435fa804-4bd5-4545-a3b6-c58ca39f1d8a	55555555-5555-5555-5555-555555555555	3	450000	M	a5cf7b9b-1c35-4408-9415-7857789b7603		\N	\N
e2d7d10f-1f70-4f2a-a8a9-7aab0c2623a6	457d4ab8-55b1-43c8-aec2-820619fc7fa6	11111111-1111-1111-1111-111111111111	2	350000	L	df8e8fea-be09-4bc4-a705-78161bee0233		\N	\N
e3a0ac07-50a8-4361-b42b-7f72e6ffeff0	bb0220b4-fba4-4abf-ab37-3f3203279b25	abb92d0f-3737-44e7-9f6a-10b5892b273a	2	100000	FREESIZE	7e2699f1-c8f7-4ee3-96c2-bf800e8982e0	Quần short đùi caro form ngắn mạc lưng đỏ	Caro Xanh - Size FREESIZE	\N
019a1161-25fc-4b0c-b6f3-9b56537bd26a	5ff195e2-9fd2-40be-93d3-8e5cde2e99c2	f8e05505-a89b-4188-a173-90b4c6db1f09	1	290000	\N	bd342b34-ff09-4dfb-be9c-7076db06c1a0		\N	\N
4ff34bc3-45fe-4550-a4bb-b049484d3acc	5ff195e2-9fd2-40be-93d3-8e5cde2e99c2	871a189b-1659-4a49-982d-0b2ff99e3eec	1	789000	\N	5c5bcc12-d8b7-4426-99f5-de7a7fceec12		\N	\N
e809100b-036e-4e81-aaac-1d4807e752b8	1110f378-e6c9-4070-ad1d-7c8cfd8ad54d	f8e05505-a89b-4188-a173-90b4c6db1f09	1	290000	\N	ee12a72c-0472-43cd-bc2c-336d2f243769		\N	\N
2f8cc660-8126-4083-a878-c91b401bceb4	1110f378-e6c9-4070-ad1d-7c8cfd8ad54d	00237cc4-4c67-4074-846c-8724b36144c5	1	189000	\N	f0d76a75-1894-415d-8857-3ceda05d2894		\N	\N
3dbb778b-da15-4a2a-b201-386c5a42a633	1110f378-e6c9-4070-ad1d-7c8cfd8ad54d	49f33164-1b39-462d-809e-9912bb9eec88	1	189000	\N	68b9c545-777d-4aff-8469-beebc950a805		\N	\N
325bb272-9cd4-446c-a3cc-08acfcc6c068	dc1c7753-cd60-40e5-9e00-ffcdcda165f3	49f33164-1b39-462d-809e-9912bb9eec88	1	189000	\N	6f792db8-123a-4d45-a9a9-965a8ca70171	ALL WIDE STRAIGHT JEANS WHOSE - Quần jeans ống đứng unisex nam nữ Whose Studio	Xanh than - Size XS	\N
\.


--
-- Data for Name: orders; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.orders (id, user_id, total_amount, shipping_address, status, created_at, payment_method, payment_status, transaction_id, order_notes, coupon_id, discount_amount, is_return_requested, return_reason, return_image_url, refunded_amount, returned_at, shipping_fee, sales_channel, source, code, customer_name, customer_phone) FROM stdin;
552046cb-2fc6-4571-bab9-dc60926c50a8	1aa70cbe-823c-4877-9344-cf1fdefced30	395000	{"city": "Thành phố Cần Thơ", "ward": "Xã Thới Hưng", "phone": "0383196830", "address": "286 Lạc Long Quân, 286 Lạc Long Quân", "district": "Huyện Cờ Đỏ", "full_name": "Lê Trần Đăng Khoa"}	completed	2026-05-05 08:13:27.026387+00	COD	paid	COD_MOCK-960301		\N	0.00	f	\N	\N	0.00	\N	45000.00	web	web	\N	\N	\N
b758fa17-9d31-4ce1-8a13-809e25bca07f	5a318635-d758-4b20-99ac-b79d097f0072	930000	{"city": "Tỉnh Bắc Kạn", "ward": "Thị trấn Chợ Rã", "phone": "0383196830", "address": "123 Lạc long quan, 124 Lạc long quan", "district": "Huyện Ba Bể", "full_name": "Khoa lê"}	pending	2026-05-06 02:04:19.153141+00	COD	pending	\N		\N	0.00	f	\N	\N	0.00	\N	30000.00	web	web	\N	\N	\N
25a25b81-de72-4831-a3bb-0c00e95c0dbf	5a318635-d758-4b20-99ac-b79d097f0072	880000	{"city": "Tỉnh Bắc Kạn", "ward": "Thị trấn Chợ Rã", "phone": "0383196830", "address": "123 Lạc long quan, 124 Lạc long quan", "district": "Huyện Ba Bể", "full_name": "Khoa lê"}	pending	2026-05-06 02:04:52.706289+00	VNPAY	pending	\N		\N	200000.00	f	\N	\N	0.00	\N	30000.00	web	web	\N	\N	\N
bd3885ae-7c17-4d00-8a40-fc99019c3343	5a318635-d758-4b20-99ac-b79d097f0072	920000	{"city": "Tỉnh Bắc Kạn", "ward": "Thị trấn Chợ Rã", "phone": "0383196830", "address": "123 Lạc long quan, 124 Lạc long quan", "district": "Huyện Ba Bể", "full_name": "Khoa lê"}	pending	2026-05-06 02:11:39.953875+00	VNPAY	pending	\N		\N	0.00	f	\N	\N	0.00	\N	30000.00	web	web	\N	\N	\N
661a642d-2c64-468a-ae02-5c600919748d	5a318635-d758-4b20-99ac-b79d097f0072	920000	{"city": "Tỉnh Bắc Kạn", "ward": "Thị trấn Chợ Rã", "phone": "0383196830", "address": "123 Lạc long quan, 124 Lạc long quan", "district": "Huyện Ba Bể", "full_name": "Khoa lê"}	pending	2026-05-06 02:11:45.628865+00	VNPAY	pending	\N		\N	0.00	f	\N	\N	0.00	\N	30000.00	web	web	\N	\N	\N
435fa804-4bd5-4545-a3b6-c58ca39f1d8a	\N	1150000	\N	completed	2026-05-06 02:30:37.842129+00	CASH	paid	\N	\N	\N	0.00	f	\N	\N	0.00	\N	0.00	pos	web	\N	\N	\N
bb0220b4-fba4-4abf-ab37-3f3203279b25	\N	200000	\N	completed	2026-05-08 07:45:51.106584+00	CASH	paid	\N	\N	\N	0.00	f	\N	\N	0.00	\N	0.00	pos	web	\N	\N	\N
5ff195e2-9fd2-40be-93d3-8e5cde2e99c2	\N	1079000	\N	completed	2026-05-08 09:03:16.354625+00	cash	paid	\N	\N	\N	0.00	f	\N	\N	0.00	\N	0.00	web	pos	POS260508160315	Khách mua tại quầy	\N
dc1c7753-cd60-40e5-9e00-ffcdcda165f3	5a318635-d758-4b20-99ac-b79d097f0072	219000	{"city": "Tỉnh Bắc Kạn", "ward": "Thị trấn Chợ Rã", "phone": "0383196830", "address": "123 Lạc long quan, 124 Lạc long quan", "district": "Huyện Ba Bể", "full_name": "Khoa lê"}	completed	2026-05-08 14:10:57.310409+00	COD	paid	COD_MOCK-443049		\N	0.00	f	\N	\N	0.00	\N	30000.00	web	web	\N	\N	\N
c701c201-3df9-4144-9381-79fa0ff6ed58	85b1983b-178f-4ab1-b8bb-6eda246ad71e	450000	{"city": "Tỉnh Bắc Kạn", "ward": "Xã Vũ Muộn", "phone": "0891263517", "address": "254, ABC", "district": "Huyện Bạch Thông", "full_name": "Lê Trần Đăng"}	packed	2026-05-04 10:19:01.331518+00	COD	pending	\N		\N	0.00	f	\N	\N	0.00	\N	0.00	web	web	\N	\N	\N
b7105c04-40df-4012-b5db-ec309c6865f5	1aa70cbe-823c-4877-9344-cf1fdefced30	1580000	{"city": "Thành phố Cần Thơ", "ward": "Xã Thới Hưng", "phone": "0383196830", "address": "286 Lạc Long Quân, 286 Lạc Long Quân", "district": "Huyện Cờ Đỏ", "full_name": "Lê Trần Đăng Khoa"}	returned	2026-05-05 03:13:07.394888+00	COD	pending	\N		\N	0.00	f	\N	\N	0.00	\N	0.00	web	web	\N	\N	\N
df33294a-185c-46b4-ac95-0c9f9e3f2de0	5a318635-d758-4b20-99ac-b79d097f0072	930000	{"city": "Tỉnh Bắc Kạn", "ward": "Thị trấn Chợ Rã", "phone": "0383196830", "address": "123 Lạc long quan, 124 Lạc long quan", "district": "Huyện Ba Bể", "full_name": "Khoa lê"}	pending	2026-05-06 01:59:25.985544+00	VNPAY	pending	\N		\N	0.00	f	\N	\N	0.00	\N	30000.00	web	web	\N	\N	\N
9952a72a-a679-4af8-aaf1-dac61e9b52b9	5a318635-d758-4b20-99ac-b79d097f0072	880000	{"city": "Tỉnh Bắc Kạn", "ward": "Thị trấn Chợ Rã", "phone": "0383196830", "address": "123 Lạc long quan, 124 Lạc long quan", "district": "Huyện Ba Bể", "full_name": "Khoa lê"}	pending	2026-05-06 02:08:17.988569+00	COD	pending	\N		\N	200000.00	f	\N	\N	0.00	\N	30000.00	web	web	\N	\N	\N
9ee3b05a-39e9-4c28-a759-f7b311f8b8b8	5a318635-d758-4b20-99ac-b79d097f0072	920000	{"city": "Tỉnh Bắc Kạn", "ward": "Thị trấn Chợ Rã", "phone": "0383196830", "address": "123 Lạc long quan, 124 Lạc long quan", "district": "Huyện Ba Bể", "full_name": "Khoa lê"}	pending	2026-05-06 02:08:36.737898+00	VNPAY	pending	\N		\N	0.00	f	\N	\N	0.00	\N	30000.00	web	web	\N	\N	\N
64b64cd1-94b4-4660-b7cd-0cfe3f8d92a3	1aa70cbe-823c-4877-9344-cf1fdefced30	1680000	{"city": "Thành phố Cần Thơ", "ward": "Xã Thới Hưng", "phone": "0383196830", "address": "286 Lạc Long Quân, 286 Lạc Long Quân", "district": "Huyện Cờ Đỏ", "full_name": "Lê Trần Đăng Khoa"}	shipped	2026-05-04 04:02:56.475344+00	COD	pending	\N		\N	0.00	f	\N	\N	0.00	\N	0.00	web	web	\N	\N	\N
8b03b65f-1d28-4c0f-b975-c748546f037a	5a318635-d758-4b20-99ac-b79d097f0072	920000	{"city": "Tỉnh Bắc Kạn", "ward": "Thị trấn Chợ Rã", "phone": "0383196830", "address": "123 Lạc long quan, 124 Lạc long quan", "district": "Huyện Ba Bể", "full_name": "Khoa lê"}	shipped	2026-05-06 02:14:01.483023+00	VNPAY	paid	15524874		\N	0.00	f	\N	\N	0.00	\N	30000.00	web	web	\N	\N	\N
74c72a61-ef43-4076-8a0c-7ac850431171	5a318635-d758-4b20-99ac-b79d097f0072	450000	{"city": "Tỉnh Bắc Kạn", "ward": "Thị trấn Chợ Rã", "phone": "0383196830", "address": "123 Lạc long quan, 124 Lạc long quan", "district": "Huyện Ba Bể", "full_name": "Khoa lê"}	shipped	2026-05-04 04:10:35.775362+00	COD	pending	\N		\N	0.00	f	\N	\N	0.00	\N	0.00	web	web	\N	\N	\N
457d4ab8-55b1-43c8-aec2-820619fc7fa6	\N	700000	\N	completed	2026-05-06 02:39:11.681791+00	CASH	paid	\N	\N	\N	0.00	f	\N	\N	0.00	\N	0.00	pos	web	\N	\N	\N
82afa8b2-c274-4eec-8d91-3c691318f59b	5a318635-d758-4b20-99ac-b79d097f0072	920000	{"city": "Tỉnh Bắc Kạn", "ward": "Thị trấn Chợ Rã", "phone": "0383196830", "address": "123 Lạc long quan, 124 Lạc long quan", "district": "Huyện Ba Bể", "full_name": "Khoa lê"}	shipped	2026-05-06 02:13:23.698971+00	VNPAY	paid	MANUAL_ADMIN_141233		\N	0.00	f	\N	\N	0.00	\N	30000.00	web	web	\N	\N	\N
98ab8098-ba4d-471a-a3aa-c60b3cb90ba9	\N	968000	\N	completed	2026-05-08 09:01:31.517412+00	cash	paid	\N	\N	\N	0.00	f	\N	\N	0.00	\N	0.00	web	pos	POS260508160131	Khách mua tại quầy	\N
1110f378-e6c9-4070-ad1d-7c8cfd8ad54d	\N	668000	\N	completed	2026-05-08 09:06:05.460834+00	cash	paid	\N	\N	\N	0.00	f	\N	\N	0.00	\N	0.00	web	pos	POS260508160605	Khách mua tại quầy	\N
\.


--
-- Data for Name: payments; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.payments (id, order_id, provider, transaction_id, amount, status, raw_response, paid_at, created_at) FROM stdin;
\.


--
-- Data for Name: permission_groups; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.permission_groups (id, name, sort_order) FROM stdin;
\.


--
-- Data for Name: permissions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.permissions (id, group_id, code, display_name, created_at) FROM stdin;
\.


--
-- Data for Name: product_analytics; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.product_analytics (id, product_id, channel, source, views, add_to_carts, sold, wishlist_count, revenue, report_date, created_at) FROM stdin;
00b5d3c5-8fa3-4b1f-a132-52b237b22590	6e5dbb16-1ab5-4c6c-8828-aa0af77bb7d7	web	organic	5	0	0	0	0.0	2026-05-08	2026-05-08 00:47:01.264984+00
7ca18899-08ba-414f-961e-846ffdcf8b41	abb92d0f-3737-44e7-9f6a-10b5892b273a	pos	direct	0	0	2	0	200000.0	2026-05-08	2026-05-08 07:45:52.10145+00
609408fb-6293-40f3-a048-c845cc349712	1cf9e9ff-f61a-472f-9d64-f8350dc55a85	web	organic	6	0	0	2	0.0	2026-05-08	2026-05-08 01:40:46.612001+00
54093e3a-c9f7-46ca-9d80-64583a4343c6	9943a8c0-dc51-4a49-918c-d56aa08d5f81	web	organic	2	0	0	1	0.0	2026-05-08	2026-05-08 02:06:35.377659+00
483f0498-3b05-4be8-9b22-508c6f4cbe5d	11111111-1111-1111-1111-111111111111	web	organic	3	0	0	6	0.0	2026-05-05	2026-05-05 13:46:32.485899+00
15358035-b56a-46bc-9dd6-5587b803f808	44444444-4444-4444-4444-444444444444	web	organic	1	0	0	0	0.0	2026-05-05	2026-05-05 13:55:14.38323+00
f2aca0f8-7c34-4c78-a938-bb4ae3bab637	55555555-5555-5555-5555-555555555555	web	organic	2	0	0	0	0.0	2026-05-05	2026-05-05 13:55:18.567982+00
e668fc50-033c-46fa-8fb9-da920e38731c	55555555-5555-5555-5555-555555555555	web	organic	0	0	4	0	1800000.0	2026-05-06	2026-05-06 01:59:26.300729+00
50f715ab-9b0f-4809-9c6f-b77c58fc8ec6	49f33164-1b39-462d-809e-9912bb9eec88	web	organic	7	3	0	4	0.0	2026-05-08	2026-05-08 01:40:44.649257+00
55b95b28-d7d9-43e1-8205-c2a113657464	11111111-1111-1111-1111-111111111111	web	organic	2	1	6	0	2100000.0	2026-05-06	2026-05-06 02:04:32.106953+00
84b90b7b-cd09-4623-a8ff-268abe2af114	55555555-5555-5555-5555-555555555555	pos	direct	0	0	3	0	1150000.0	2026-05-06	2026-05-06 02:30:38.637916+00
9c243f8c-e620-43a2-be0e-cd498867cd36	11111111-1111-1111-1111-111111111111	pos	direct	0	0	2	0	700000.0	2026-05-06	2026-05-06 02:39:12.455772+00
ba568d48-f889-44a0-9e4c-dafe92ab9690	44444444-4444-4444-4444-444444444444	web	organic	1	1	5	0	4450000.0	2026-05-06	2026-05-06 02:08:37.033955+00
2813d347-91dd-4e43-949b-8a93d8940431	55555555-5555-5555-5555-555555555555	web	organic	1	0	0	0	0.0	2026-05-07	2026-05-07 01:50:26.161011+00
033b37a2-d16e-4e3e-a12e-b836d3d497b5	33333333-3333-3333-3333-333333333333	web	organic	2	0	0	0	0.0	2026-05-07	2026-05-07 01:29:34.004442+00
d91750a9-4bc1-40e3-998a-c54eb5fcfc2e	f8e05505-a89b-4188-a173-90b4c6db1f09	web	organic	2	0	0	7	0.0	2026-05-07	2026-05-07 01:32:16.844167+00
380e785f-8ad7-4854-83ad-843d100325df	00237cc4-4c67-4074-846c-8724b36144c5	web	organic	1	0	0	1	0.0	2026-05-07	2026-05-07 06:51:50.262523+00
58801b93-e267-4363-a9c7-c5e5ce2ce2e0	6538dbcf-35ea-45f0-a4d8-8ec3a2439768	web	organic	1	0	0	0	0.0	2026-05-07	2026-05-07 06:52:23.991019+00
bc3d00f2-de7a-492a-96bf-c471b579e1c3	49f33164-1b39-462d-809e-9912bb9eec88	web	organic	1	0	0	1	0.0	2026-05-07	2026-05-07 16:26:54.541331+00
2eb8f65a-8eac-4194-9973-307993cb401e	00237cc4-4c67-4074-846c-8724b36144c5	web	organic	2	0	0	0	0.0	2026-05-08	2026-05-08 00:46:52.992848+00
7f4f4768-ce20-4c6c-bba8-f8a6f5e5d71b	3a2c99a1-6932-43b7-858f-0fc1789a85e7	web	organic	2	0	0	0	0.0	2026-05-08	2026-05-08 03:13:27.104791+00
\.


--
-- Data for Name: product_images; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.product_images (id, product_id, url, is_primary, sort_order) FROM stdin;
d46dfdfd-1bc1-443a-b395-f0c8771053d5	22222222-2222-2222-2222-222222222222	https://images.unsplash.com/photo-1556821840-3a63f15732ce?w=600	t	0
20ad3645-c065-40e9-ba16-3197feb4759e	22222222-2222-2222-2222-222222222222	https://images.unsplash.com/photo-1509942774463-acf339cf87d5?w=600	f	1
63f792b3-4c74-4877-ad45-57e58c0cad89	44444444-4444-4444-4444-444444444444	https://images.unsplash.com/photo-1591047139829-d91aecb6caea?w=600	t	0
73e49308-b280-434a-bc7a-dc3fe5b30622	44444444-4444-4444-4444-444444444444	https://images.unsplash.com/photo-1548126032-079a0fb0099d?w=600	f	1
ec42e18e-555b-4591-b49b-db753a5c43d2	55555555-5555-5555-5555-555555555555	https://images.unsplash.com/photo-1586363104862-3a5e2ab60d99?w=600	t	0
7b6a552f-088a-4999-940b-bdad0d5b93cc	33333333-3333-3333-3333-333333333333	https://images.unsplash.com/photo-1542272604-787c3835535d?w=600	t	0
8f273c7f-a276-4884-aafb-c6d0fae53ae6	11111111-1111-1111-1111-111111111111	https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=600	t	0
ad09042e-d8e2-41cb-bfb0-1d646169747e	11111111-1111-1111-1111-111111111111	https://images.unsplash.com/photo-1503341504253-dff4815485f1?w=600	f	1
17dab94e-74f2-4546-ab67-649bc63c0746	871a189b-1659-4a49-982d-0b2ff99e3eec	https://static.zara.net/assets/public/1366/ac2e/104a48c4bbf8/394d2d730174/02722172700-p/02722172700-p.jpg?ts=1775058838306&w=1024	t	0
3c1358c6-607d-43df-bed1-4c4b5bc29841	871a189b-1659-4a49-982d-0b2ff99e3eec	https://static.zara.net/assets/public/5c66/734d/81594e2cb7f0/bde1fbbe0b02/02722172700-a1/02722172700-a1.jpg?ts=1775058839096&w=1126	f	1
0fe6fcbe-fe82-488a-86cd-83bbeab71051	871a189b-1659-4a49-982d-0b2ff99e3eec	https://static.zara.net/assets/public/0409/e2b9/ec7d420e96a0/3608df346475/02722172700-a2/02722172700-a2.jpg?ts=1775058838383&w=750	f	2
9aa61388-dcf0-4fea-acfb-d57815f45952	f8e05505-a89b-4188-a173-90b4c6db1f09	https://down-vn.img.susercontent.com/file/vn-11134207-820l4-meifryxnonice5.webp	t	0
aaa03910-2c03-4d3d-88c8-ac45a40e9402	f8e05505-a89b-4188-a173-90b4c6db1f09	https://down-vn.img.susercontent.com/file/vn-11134207-820l4-mf103u48jehbe6.webp	f	1
2778ce91-32c1-4cdc-bfa9-ccff28cec405	00237cc4-4c67-4074-846c-8724b36144c5	https://down-vn.img.susercontent.com/file/vn-11134207-81ztc-mnuy30h1ys5f7a.webp	t	0
66449db9-e4f3-4e44-9332-ed656ae88fbc	00237cc4-4c67-4074-846c-8724b36144c5	https://down-vn.img.susercontent.com/file/vn-11134207-81ztc-mnuxz6g311c063.webp	f	1
db731363-d1c8-4f34-84a9-2f7f2ccd43b1	00237cc4-4c67-4074-846c-8724b36144c5	https://down-vn.img.susercontent.com/file/vn-11134207-81ztc-mnuxz6ghqlfs34.webp	f	2
7752d8e8-10e8-4482-9cc0-d34e097899d4	6538dbcf-35ea-45f0-a4d8-8ec3a2439768	https://down-vn.img.susercontent.com/file/vn-11134207-81ztc-ml5wuamm2qdp41.webp	t	0
b8a25f83-980f-4ee4-a163-d5834fd8e103	6538dbcf-35ea-45f0-a4d8-8ec3a2439768	https://down-vn.img.susercontent.com/file/vn-11134207-81ztc-ml5wuamm44y5b9.webp	f	1
d920f4d5-ebe3-4df5-9c34-4a5cfcb78033	6538dbcf-35ea-45f0-a4d8-8ec3a2439768	https://down-vn.img.susercontent.com/file/vn-11134207-81ztc-ml5wuamo0yrmcc.webp	f	2
864fafbb-7ff6-4ce8-a7d0-a8e031e95f1c	6538dbcf-35ea-45f0-a4d8-8ec3a2439768	https://down-vn.img.susercontent.com/file/vn-11134207-81ztc-ml5wuamm6y3153.webp	f	3
1457cea4-a447-4a2c-90d2-35c19981c951	abb92d0f-3737-44e7-9f6a-10b5892b273a	https://down-vn.img.susercontent.com/file/vn-11134207-820l4-mgq5u3k0lrt656.webp	t	0
c1c3a72e-ac82-46dd-99b5-9cf84f924c3a	abb92d0f-3737-44e7-9f6a-10b5892b273a	https://down-vn.img.susercontent.com/file/vn-11134207-820l4-mgq5u3kb0tfv5d.webp	f	1
4ddb01f4-a4d0-4d1f-8dcb-37501bd5f57c	6e5dbb16-1ab5-4c6c-8828-aa0af77bb7d7	https://down-vn.img.susercontent.com/file/vn-11134207-7ras8-mb55i8sd9q6v10.webp	t	0
802a9860-3443-4866-baa7-63cbf96d9037	6e5dbb16-1ab5-4c6c-8828-aa0af77bb7d7	https://down-vn.img.susercontent.com/file/vn-11134207-7ra0g-m6nruqg98dp406.webp	f	1
51b22b42-8a55-44d5-9354-91bd3ba86b5b	3a2c99a1-6932-43b7-858f-0fc1789a85e7	https://down-vn.img.susercontent.com/file/vn-11134207-7ra0g-m9l9ts4c2o7u8c@resize_w900_nl.webp	t	0
49d9e7f4-ac40-4490-9647-f9b2bf874df8	3a2c99a1-6932-43b7-858f-0fc1789a85e7	https://down-vn.img.susercontent.com/file/vn-11134207-7ra0g-m9l9ym9d8pda70@resize_w900_nl.webp	f	1
f23eb319-1399-4e45-b133-18e442296cf1	3a2c99a1-6932-43b7-858f-0fc1789a85e7	https://down-vn.img.susercontent.com/file/vn-11134207-820l4-mghmkukmlqmlb6@resize_w900_nl.webp	f	2
487f24c5-38f9-4f46-b7e6-6a1b89397a7b	9943a8c0-dc51-4a49-918c-d56aa08d5f81	https://down-vn.img.susercontent.com/file/vn-11134207-820l4-mj9w5s5c5yww80.webp	t	0
268f2ca6-4a2a-4bdf-a1ab-ec71670adf90	9943a8c0-dc51-4a49-918c-d56aa08d5f81	https://down-vn.img.susercontent.com/file/vn-11134207-820l4-mj9w5s5179c604.webp	f	1
603dd43f-70ae-4fea-9a1b-1702273bfed7	1cf9e9ff-f61a-472f-9d64-f8350dc55a85	https://down-vn.img.susercontent.com/file/vn-11134207-7ras8-marzarcl5k9k85.webp	t	0
7795b01a-b6a2-4ab4-b078-38fc45259625	1cf9e9ff-f61a-472f-9d64-f8350dc55a85	https://down-vn.img.susercontent.com/file/vn-11134207-7ras8-marzarcl6yu061.webp	f	1
cfa5e9df-d782-4841-b25b-f6d2bd442639	1cf9e9ff-f61a-472f-9d64-f8350dc55a85	https://down-vn.img.susercontent.com/file/vn-11134207-7ras8-marzarcl2r4o3c.webp	f	2
e8d7c253-27cc-4694-be1f-85f3fb9f1b97	49f33164-1b39-462d-809e-9912bb9eec88	https://down-vn.img.susercontent.com/file/vn-11134207-820l4-mhbnngbz09ovce.webp	t	0
149aee34-aa9d-46b4-a695-bd3beb7c58e4	49f33164-1b39-462d-809e-9912bb9eec88	https://down-vn.img.susercontent.com/file/vn-11134207-820l4-mhbnnz3h3fv20e.webp	f	1
c06bed54-4f8f-4174-8fa8-84dddb6dd0ba	49f33164-1b39-462d-809e-9912bb9eec88	https://down-vn.img.susercontent.com/file/vn-11134207-7ras8-mb6lrpqsd8ld86.webp	f	2
fa1da2cd-294a-45c2-80ac-91b85e8d971b	49f33164-1b39-462d-809e-9912bb9eec88	https://down-vn.img.susercontent.com/file/vn-11134207-820l4-mhbno4ysr6z25f.webp	f	3
eb67fd2b-c75a-4501-aa3b-c3d1da1cad8c	49f33164-1b39-462d-809e-9912bb9eec88	https://down-vn.img.susercontent.com/file/vn-11134207-820l4-mhbnoab3louh10.webp	f	4
\.


--
-- Data for Name: product_reviews; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.product_reviews (id, product_id, user_id, order_id, rating, comment, images, reply_comment, is_hidden, created_at) FROM stdin;
\.


--
-- Data for Name: product_variants; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.product_variants (id, product_id, size, color_name, color_hex, sku, price_override, stock, created_at) FROM stdin;
bd342b34-ff09-4dfb-be9c-7076db06c1a0	f8e05505-a89b-4188-a173-90b4c6db1f09	L	Đen	#1c1917	\N	\N	4	2026-05-06 08:48:12.641356+00
5c5bcc12-d8b7-4426-99f5-de7a7fceec12	871a189b-1659-4a49-982d-0b2ff99e3eec	M	Đen	#1c1917	\N	\N	29	2026-05-06 07:11:08.357334+00
ee12a72c-0472-43cd-bc2c-336d2f243769	f8e05505-a89b-4188-a173-90b4c6db1f09	M	Xám	#1c1917	\N	\N	4	2026-05-06 08:48:12.641356+00
f0d76a75-1894-415d-8857-3ceda05d2894	00237cc4-4c67-4074-846c-8724b36144c5	M	Xanh	#0bfafe	\N	\N	19	2026-05-07 06:51:10.463162+00
054a5a46-6461-44bf-92e5-c4d91f6babee	22222222-2222-2222-2222-222222222222	S	Xám	#78716c	\N	\N	5	2026-05-03 01:31:58.35934+00
f3fa6480-a09b-46e8-a439-339f97d2ea83	22222222-2222-2222-2222-222222222222	M	Xám	#78716c	\N	\N	8	2026-05-03 01:31:58.35934+00
6d561497-f4d2-4d51-aef7-711b07b7e993	22222222-2222-2222-2222-222222222222	L	Xám	#78716c	\N	\N	10	2026-05-03 01:31:58.35934+00
1a64f10f-c6ce-4685-a10f-c25a0f286e53	22222222-2222-2222-2222-222222222222	XL	Xám	#78716c	\N	\N	7	2026-05-03 01:31:58.35934+00
8cdcd3af-1656-4204-a317-38193f93fbc7	22222222-2222-2222-2222-222222222222	S	Đen	#1c1917	\N	680000	3	2026-05-03 01:31:58.35934+00
7154fd17-ca86-405f-af65-165e9dbce68f	22222222-2222-2222-2222-222222222222	M	Đen	#1c1917	\N	680000	5	2026-05-03 01:31:58.35934+00
9f6e3bf5-c1f5-4a24-bb00-d0d32761b824	22222222-2222-2222-2222-222222222222	L	Đen	#1c1917	\N	680000	0	2026-05-03 01:31:58.35934+00
1e5fd436-ef31-480b-8ccb-06058343f24f	22222222-2222-2222-2222-222222222222	XL	Đen	#1c1917	\N	680000	2	2026-05-03 01:31:58.35934+00
d57f2203-4680-431f-a2ad-b8941112dfed	44444444-4444-4444-4444-444444444444	S	Trắng	#ffffff	\N	\N	3	2026-05-03 01:31:58.35934+00
7070ea44-bdc3-46a0-aa1e-d7bc2e4a5ed8	44444444-4444-4444-4444-444444444444	M	Trắng	#ffffff	\N	\N	5	2026-05-03 01:31:58.35934+00
347fb8ea-d7c9-42b7-b873-02a819a28168	44444444-4444-4444-4444-444444444444	L	Trắng	#ffffff	\N	\N	4	2026-05-03 01:31:58.35934+00
9ed3bb23-ec93-4ccc-830b-8d9acf2aff3c	44444444-4444-4444-4444-444444444444	XL	Trắng	#ffffff	\N	\N	3	2026-05-03 01:31:58.35934+00
27733798-99e4-40e4-9e12-533da87ab1c4	44444444-4444-4444-4444-444444444444	S	Đen	#1c1917	\N	920000	2	2026-05-03 01:31:58.35934+00
47a28d37-1827-4acb-b60f-b1fd01509de4	44444444-4444-4444-4444-444444444444	M	Đen	#1c1917	\N	920000	3	2026-05-03 01:31:58.35934+00
0a3b1f62-42de-4926-8f0f-a0126691d6bf	44444444-4444-4444-4444-444444444444	L	Đen	#1c1917	\N	920000	0	2026-05-03 01:31:58.35934+00
3964fa68-4bf1-4846-aae7-01fed71cdcb6	55555555-5555-5555-5555-555555555555	S	Kem	#fef3c7	\N	\N	8	2026-05-03 01:31:58.35934+00
e881b370-3bb8-4d35-b180-a6f5bc2314dc	55555555-5555-5555-5555-555555555555	M	Kem	#fef3c7	\N	\N	12	2026-05-03 01:31:58.35934+00
7805a371-a6f0-4060-acdc-90d2987070d7	55555555-5555-5555-5555-555555555555	L	Kem	#fef3c7	\N	\N	10	2026-05-03 01:31:58.35934+00
73d0e57b-9486-44b1-9d4e-42f9f898cb5c	55555555-5555-5555-5555-555555555555	XL	Kem	#fef3c7	\N	\N	5	2026-05-03 01:31:58.35934+00
7d075366-c0c7-4976-88bd-dbe2292c22ee	55555555-5555-5555-5555-555555555555	S	Xanh Dương	#3b82f6	\N	450000	4	2026-05-03 01:31:58.35934+00
6e8a6232-1e32-4a75-9884-11b5094e86bf	55555555-5555-5555-5555-555555555555	L	Xanh Dương	#3b82f6	\N	450000	3	2026-05-03 01:31:58.35934+00
5d9cade3-41bc-495c-90dd-c076bc97c9c0	33333333-3333-3333-3333-333333333333	S	Xanh Navy	#1e3a8a	\N	\N	5	2026-05-03 04:55:11.581417+00
0a5607b4-effb-4762-aeee-3b23390e3ac7	33333333-3333-3333-3333-333333333333	M	Xanh Navy	#1e3a8a	\N	\N	8	2026-05-03 04:55:11.581417+00
dc2fade2-a553-422d-afdf-b4db2ae81b99	33333333-3333-3333-3333-333333333333	L	Xanh Navy	#1e3a8a	\N	\N	7	2026-05-03 04:55:11.581417+00
ef953bc6-19f5-429a-b63b-ccb72df6260e	33333333-3333-3333-3333-333333333333	XL	Xanh Navy	#1e3a8a	\N	\N	5	2026-05-03 04:55:11.581417+00
e3f92e2a-25c7-44b5-9b45-9cd4b9f8bbbd	33333333-3333-3333-3333-333333333333	S	Trắng	#ffffff	\N	\N	3	2026-05-03 04:55:11.581417+00
6171bd76-b801-4364-802d-2acf0e52d641	33333333-3333-3333-3333-333333333333	M	Trắng	#ffffff	\N	\N	4	2026-05-03 04:55:11.581417+00
857b5b65-2544-4897-a145-ca1e71647151	33333333-3333-3333-3333-333333333333	L	Trắng	#ffffff	\N	\N	3	2026-05-03 04:55:11.581417+00
6f38bad3-d3f6-4243-b017-30bc00d6eb15	11111111-1111-1111-1111-111111111111	S	Đen	#1c1917	\N	\N	10	2026-05-05 03:14:08.523687+00
0588b6b7-e639-4a56-a894-d21d123927ff	11111111-1111-1111-1111-111111111111	M	Đen	#1c1917	\N	\N	15	2026-05-05 03:14:08.523687+00
6260ec38-ef08-49d0-9c95-fee8c821ad84	11111111-1111-1111-1111-111111111111	XL	Đen	#1c1917	\N	\N	10	2026-05-05 03:14:08.523687+00
8494ce4e-09a8-4c39-a4a6-c77591e32a84	11111111-1111-1111-1111-111111111111	S	Trắng	#ffffff	\N	\N	8	2026-05-05 03:14:08.523687+00
7c76f823-a0b5-44c2-8307-5528d0dd2cd3	11111111-1111-1111-1111-111111111111	M	Trắng	#ffffff	\N	\N	12	2026-05-05 03:14:08.523687+00
78651b21-e89f-4ad6-9d84-e079476382e9	11111111-1111-1111-1111-111111111111	L	Trắng	#ffffff	\N	\N	0	2026-05-05 03:14:08.523687+00
cc035689-aa92-402a-a93e-87791640bd81	11111111-1111-1111-1111-111111111111	XL	Trắng	#ffffff	\N	\N	5	2026-05-05 03:14:08.523687+00
a5cf7b9b-1c35-4408-9415-7857789b7603	55555555-5555-5555-5555-555555555555	M	Xanh Dương	#3b82f6	\N	450000	3	2026-05-03 01:31:58.35934+00
df8e8fea-be09-4bc4-a705-78161bee0233	11111111-1111-1111-1111-111111111111	L	Đen	#1c1917	\N	\N	13	2026-05-05 03:14:08.523687+00
37224df3-e3b1-41ff-811a-a3936f376246	871a189b-1659-4a49-982d-0b2ff99e3eec	S	Đen	#1c1917	\N	\N	20	2026-05-06 07:11:08.357334+00
caeba279-c9ac-49c6-ac59-0c0111065676	871a189b-1659-4a49-982d-0b2ff99e3eec	L	Đen	#1c1917	\N	\N	50	2026-05-06 07:11:08.357334+00
bac4a0a6-0262-4754-b15d-2202adc2a155	f8e05505-a89b-4188-a173-90b4c6db1f09	S	Đen	#1c1917	\N	\N	5	2026-05-06 08:48:12.641356+00
56891f98-285d-4c47-bd40-f0fbe3c0061b	f8e05505-a89b-4188-a173-90b4c6db1f09	M	Đen	#1c1917	\N	\N	5	2026-05-06 08:48:12.641356+00
013cde3f-937b-4e9d-aba8-130df4d5d181	f8e05505-a89b-4188-a173-90b4c6db1f09	S	Xám	#1c1917	\N	\N	5	2026-05-06 08:48:12.641356+00
b8ae4f20-df20-4763-b00d-657858863018	f8e05505-a89b-4188-a173-90b4c6db1f09	L	Xám	#1c1917	\N	\N	5	2026-05-06 08:48:12.641356+00
9da78347-e0b8-4151-a6a2-8ed45f22cd62	00237cc4-4c67-4074-846c-8724b36144c5	S	Vàng	#fef606	\N	\N	20	2026-05-07 06:51:10.463162+00
93e06078-9131-4a22-a311-5f7cc929310a	00237cc4-4c67-4074-846c-8724b36144c5	M	Vàng	#fef606	\N	\N	20	2026-05-07 06:51:10.463162+00
081ce261-5c40-4bb6-9f7f-abfb8b6462e6	00237cc4-4c67-4074-846c-8724b36144c5	S	Xanh	#0bfafe	\N	\N	20	2026-05-07 06:51:10.463162+00
0d27db24-647d-41ee-a9f6-446a549192ef	6538dbcf-35ea-45f0-a4d8-8ec3a2439768	M	Đen	#1c1917	\N	\N	20	2026-05-07 06:51:20.505321+00
e3ddc634-d6d3-4fc4-ada3-d5028db08e62	6538dbcf-35ea-45f0-a4d8-8ec3a2439768	S	Đen	#1c1917	\N	\N	20	2026-05-07 06:51:20.505321+00
04653f16-d6e2-419c-87d6-006d02cf9e0b	6538dbcf-35ea-45f0-a4d8-8ec3a2439768	L	Đen	#1c1917	\N	\N	20	2026-05-07 06:51:20.505321+00
1b4252e7-2cec-415a-b03e-7da90a92e026	6538dbcf-35ea-45f0-a4d8-8ec3a2439768	XL	Đen	#1c1917	\N	\N	20	2026-05-07 06:51:20.505321+00
2d8bbfd8-e1b3-466b-afca-54df18d97c40	6538dbcf-35ea-45f0-a4d8-8ec3a2439768	L	Xám	#cfcfcf	\N	\N	20	2026-05-07 06:51:20.505321+00
eb1f3cc4-9e78-4142-bbc4-a2e358b6630d	6538dbcf-35ea-45f0-a4d8-8ec3a2439768	M	Xám	#cfcfcf	\N	\N	20	2026-05-07 06:51:20.505321+00
034a3248-5b24-4d2b-b887-cadfb5fb4c40	6538dbcf-35ea-45f0-a4d8-8ec3a2439768	S	Xám	#cfcfcf	\N	\N	20	2026-05-07 06:51:20.505321+00
4290be2f-6fb6-47dc-8081-df28dd080046	6538dbcf-35ea-45f0-a4d8-8ec3a2439768	XL	Xám	#cfcfcf	\N	\N	20	2026-05-07 06:51:20.505321+00
86e310ea-9539-4ae6-9120-b818cc526d95	6538dbcf-35ea-45f0-a4d8-8ec3a2439768	M	Xám nâu	#866c5b	\N	\N	20	2026-05-07 06:51:20.505321+00
c286b067-013f-468f-add0-44b97aeb09ea	6538dbcf-35ea-45f0-a4d8-8ec3a2439768	S	Xám nâu	#866c5b	\N	\N	20	2026-05-07 06:51:20.505321+00
4a7e131c-edad-4392-9399-aa8e0a110d4a	6538dbcf-35ea-45f0-a4d8-8ec3a2439768	L	Xám nâu	#866c5b	\N	\N	20	2026-05-07 06:51:20.505321+00
4344d0b6-d062-4498-b27e-6b3577854a0c	6538dbcf-35ea-45f0-a4d8-8ec3a2439768	XL	Xám nâu	#866c5b	\N	\N	20	2026-05-07 06:51:20.505321+00
1258a189-2dd7-4930-bcf2-4ff64d498e43	abb92d0f-3737-44e7-9f6a-10b5892b273a	FREESIZE	Caro Đỏ	#8c0808	\N	\N	20	2026-05-07 06:51:29.187805+00
33c9df54-a601-4699-b7ef-a0f7ec96ab4a	6e5dbb16-1ab5-4c6c-8828-aa0af77bb7d7	M	Đen	#1c1917	\N	\N	5	2026-05-07 16:05:49.354069+00
77d8d346-7f4a-4dbf-bf7a-90c17a37c146	6e5dbb16-1ab5-4c6c-8828-aa0af77bb7d7	L	Đen	#1c1917	\N	\N	5	2026-05-07 16:05:49.354069+00
9893472b-5e07-41a9-8bbd-e088c260ef05	6e5dbb16-1ab5-4c6c-8828-aa0af77bb7d7	XL	Đen	#1c1917	\N	\N	3	2026-05-07 16:05:49.354069+00
bc48bfa8-b372-4c6c-9359-cafd46e05a53	6e5dbb16-1ab5-4c6c-8828-aa0af77bb7d7	M	Xám	#c2c2c2	\N	\N	5	2026-05-07 16:05:49.354069+00
ee0c11ee-255d-41c5-bd9c-ff4054eca17f	6e5dbb16-1ab5-4c6c-8828-aa0af77bb7d7	L	Xám	#c2c2c2	\N	\N	5	2026-05-07 16:05:49.354069+00
47b33602-0500-4c07-86c1-f9134eb75547	6e5dbb16-1ab5-4c6c-8828-aa0af77bb7d7	XL	Xám	#c2c2c2	\N	\N	5	2026-05-07 16:05:49.354069+00
5ec6fb64-0937-418c-9eb7-fd2957f8cf4a	3a2c99a1-6932-43b7-858f-0fc1789a85e7	S	Xám Trắng	#d6d6d6	\N	\N	5	2026-05-07 16:10:52.978436+00
469ea57b-e797-4ea3-8e59-fd8f4fece64d	3a2c99a1-6932-43b7-858f-0fc1789a85e7	M	Xám Trắng	#d6d6d6	\N	\N	5	2026-05-07 16:10:52.978436+00
b7edbd9d-fec7-45d3-b6cf-35e2c8fe1e72	3a2c99a1-6932-43b7-858f-0fc1789a85e7	L	Xám Trắng	#d6d6d6	\N	\N	5	2026-05-07 16:10:52.978436+00
9ec4551d-4d22-4c5d-85fd-f3492666c9d6	3a2c99a1-6932-43b7-858f-0fc1789a85e7	S	Xanh da trời	#00c8fa	\N	\N	6	2026-05-07 16:10:52.978436+00
d62c03f2-0687-42da-b78a-69e2b23786bd	3a2c99a1-6932-43b7-858f-0fc1789a85e7	M	Xanh da trời	#00c8fa	\N	\N	6	2026-05-07 16:10:52.978436+00
7d2ca183-3aae-432b-a3ef-f439a74b325a	3a2c99a1-6932-43b7-858f-0fc1789a85e7	L	Xanh da trời	#00c8fa	\N	\N	6	2026-05-07 16:10:52.978436+00
095b264f-5eb6-469d-8505-6076f05a9301	3a2c99a1-6932-43b7-858f-0fc1789a85e7	S	Xanh than	#2c88af	\N	\N	4	2026-05-07 16:10:52.978436+00
ef370f52-2911-4548-9701-a0d8a8d9aead	3a2c99a1-6932-43b7-858f-0fc1789a85e7	M	Xanh than	#2c88af	\N	\N	4	2026-05-07 16:10:52.978436+00
6171bcbc-2e04-4ec7-aa71-b52b2a825147	3a2c99a1-6932-43b7-858f-0fc1789a85e7	L	Xanh than	#2c88af	\N	\N	4	2026-05-07 16:10:52.978436+00
db7ffc2a-8f47-4701-a356-2e019ebb32a0	9943a8c0-dc51-4a49-918c-d56aa08d5f81	S	Đỏ đô	#b13939	\N	\N	5	2026-05-07 16:13:57.41632+00
c0e808d7-dbf2-4387-b3ea-b34cb8732a08	9943a8c0-dc51-4a49-918c-d56aa08d5f81	M	Đỏ đô	#b13939	\N	\N	5	2026-05-07 16:13:57.41632+00
f64e583e-25a0-45be-a095-e19c3da00d17	9943a8c0-dc51-4a49-918c-d56aa08d5f81	L	Đỏ đô	#b13939	\N	\N	5	2026-05-07 16:13:57.41632+00
f08d5a6f-7be8-4bb1-85ff-7d485af2a114	9943a8c0-dc51-4a49-918c-d56aa08d5f81	S	Xanh bộ đội	#51733f	\N	\N	6	2026-05-07 16:13:57.41632+00
0a53c483-c1dc-4c2a-ba11-eb089114ce54	9943a8c0-dc51-4a49-918c-d56aa08d5f81	M	Xanh bộ đội	#51733f	\N	\N	7	2026-05-07 16:13:57.41632+00
795e811f-592b-42e9-89e5-52e1a88eb4e5	9943a8c0-dc51-4a49-918c-d56aa08d5f81	L	Xanh bộ đội	#51733f	\N	\N	5	2026-05-07 16:13:57.41632+00
6f792db8-123a-4d45-a9a9-965a8ca70171	49f33164-1b39-462d-809e-9912bb9eec88	XS	Xanh than	#024388	\N	\N	3	2026-05-07 16:26:05.833892+00
cb7bc29f-68d0-45bf-ba7e-b259eef8111d	49f33164-1b39-462d-809e-9912bb9eec88	S	Xanh than	#024388	\N	\N	3	2026-05-07 16:26:05.833892+00
7482a33c-fa61-4c0c-a692-2bbafa87714e	49f33164-1b39-462d-809e-9912bb9eec88	L	Xanh than	#024388	\N	\N	3	2026-05-07 16:26:05.833892+00
a7471c6f-5b38-4098-b293-a577e5e8c2ab	49f33164-1b39-462d-809e-9912bb9eec88	S	Đen	#1c1917	\N	\N	3	2026-05-07 16:26:05.833892+00
29eae69a-f6da-4f25-9652-fed8f34ffdb0	49f33164-1b39-462d-809e-9912bb9eec88	M	Đen	#1c1917	\N	\N	3	2026-05-07 16:26:05.833892+00
78f8cf3b-5e7f-4dc9-a392-8c7f0065d554	49f33164-1b39-462d-809e-9912bb9eec88	L	Đen	#1c1917	\N	\N	3	2026-05-07 16:26:05.833892+00
c8b1f524-3649-4859-839e-dda1e8aa114b	49f33164-1b39-462d-809e-9912bb9eec88	XL	Đen	#1c1917	\N	\N	2	2026-05-07 16:26:05.833892+00
172925c3-247f-4d90-80ea-1a76b6c4e46e	49f33164-1b39-462d-809e-9912bb9eec88	XS	Xanh dương	#78b2ce	\N	\N	4	2026-05-07 16:26:05.833892+00
cf0ee1cd-ebfc-4447-872f-cdc1b41ba6b8	1cf9e9ff-f61a-472f-9d64-f8350dc55a85	S	Xanh navy	#023374	\N	\N	2	2026-05-07 16:21:36.152173+00
8c764649-dc25-43cb-9f38-d6aeff92d65c	1cf9e9ff-f61a-472f-9d64-f8350dc55a85	M	Xanh navy	#023374	\N	\N	2	2026-05-07 16:21:36.152173+00
db30a408-e495-4920-9d97-f322e4669a43	1cf9e9ff-f61a-472f-9d64-f8350dc55a85	L	Xanh navy	#023374	\N	\N	2	2026-05-07 16:21:36.152173+00
7072242c-f252-423f-b7c1-f5d300fc3acf	1cf9e9ff-f61a-472f-9d64-f8350dc55a85	S	Vàng	#fbc913	\N	\N	3	2026-05-07 16:21:36.152173+00
192f6992-7355-48a1-b014-345eec387adc	1cf9e9ff-f61a-472f-9d64-f8350dc55a85	M	Vàng	#fbc913	\N	\N	3	2026-05-07 16:21:36.152173+00
49ff45f0-5ff8-414c-bf66-94f96743444d	1cf9e9ff-f61a-472f-9d64-f8350dc55a85	L	Vàng	#fbc913	\N	\N	3	2026-05-07 16:21:36.152173+00
8308d373-d148-4966-8a1f-7fe32ded2bab	1cf9e9ff-f61a-472f-9d64-f8350dc55a85	S	Xanh dương	#b2d9dc	\N	\N	6	2026-05-07 16:21:36.152173+00
3fbab88e-dca2-4f56-a321-83ca41349a41	1cf9e9ff-f61a-472f-9d64-f8350dc55a85	M	Xanh dương	#b2d9dc	\N	\N	3	2026-05-07 16:21:36.152173+00
c31733cc-3916-4cae-adb8-4f03d0e73dbe	1cf9e9ff-f61a-472f-9d64-f8350dc55a85	L	Xanh dương	#b2d9dc	\N	\N	4	2026-05-07 16:21:36.152173+00
ee350abe-bfbe-4e3d-b2e9-371754d6a56c	49f33164-1b39-462d-809e-9912bb9eec88	S	Xanh dương	#78b2ce	\N	\N	4	2026-05-07 16:26:05.833892+00
824bdc6d-daea-414a-adbf-2ba1e3ec5c4f	49f33164-1b39-462d-809e-9912bb9eec88	M	Xanh dương	#78b2ce	\N	\N	4	2026-05-07 16:26:05.833892+00
b42cffa6-44c0-47f7-8acf-d1c16aa7c2b9	49f33164-1b39-462d-809e-9912bb9eec88	L	Xanh dương	#78b2ce	\N	\N	4	2026-05-07 16:26:05.833892+00
1b8d1391-d85b-4499-812e-c867920fcb66	49f33164-1b39-462d-809e-9912bb9eec88	M	Nâu	#815d46	\N	\N	4	2026-05-07 16:26:05.833892+00
c8b68825-03c1-4091-8425-7c2944198ac6	49f33164-1b39-462d-809e-9912bb9eec88	S	Nâu	#815d46	\N	\N	4	2026-05-07 16:26:05.833892+00
cdbfd459-1ad7-4b90-bac7-ebc159bd152b	49f33164-1b39-462d-809e-9912bb9eec88	L	Nâu	#815d46	\N	\N	4	2026-05-07 16:26:05.833892+00
0f109576-bc6d-4cf7-b814-89c792cd45d5	49f33164-1b39-462d-809e-9912bb9eec88	XL	Nâu	#815d46	\N	\N	3	2026-05-07 16:26:05.833892+00
7e2699f1-c8f7-4ee3-96c2-bf800e8982e0	abb92d0f-3737-44e7-9f6a-10b5892b273a	FREESIZE	Caro Xanh	#003f7a	\N	\N	18	2026-05-07 06:51:29.187805+00
68b9c545-777d-4aff-8469-beebc950a805	49f33164-1b39-462d-809e-9912bb9eec88	M	Xanh than	#024388	\N	\N	2	2026-05-07 16:26:05.833892+00
\.


--
-- Data for Name: products; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.products (id, name, description, price, stock, category_id, thumbnail_url, is_featured, is_active, created_at, rating, sold_count, discount, slug, meta_title, meta_description, brand, gender, tags, deleted_at, created_by, brand_id, attributes) FROM stdin;
22222222-2222-2222-2222-222222222222	Hoodie Oversized GUA Xám	Hoodie form rộng phong cách streetwear. Chất nỉ dày dặn, ấm áp, túi kangaroo tiện dụng.	650000	30	\N	https://images.unsplash.com/photo-1556821840-3a63f15732ce?w=600	t	f	2026-05-03 01:31:58.35934+00	4.5	0	0	hoodie-oversized-gua-xam	\N	\N	GUA Maison	unisex	\N	2026-05-03 11:43:46.466991+00	\N	\N	{}
44444444-4444-4444-4444-444444444444	Áo Khoác Bomber GUA Trắng	Áo khoác bomber phong cách retro. Lớp lót ấm, thiết kế cổ điển phù hợp mọi outfit.	890000	15	\N	https://images.unsplash.com/photo-1591047139829-d91aecb6caea?w=600	t	f	2026-05-03 01:31:58.35934+00	4.5	0	0	ao-khoac-bomber-gua-trang	\N	\N	GUA Maison	unisex	\N	2026-05-07 10:13:51.657876+00	\N	\N	{}
871a189b-1659-4a49-982d-0b2ff99e3eec	ÁO KHOÁC BLAZER VẢI PHA LINEN ZW COLLECTION	Áo khoác blazer vải pha sợi linen. Cổ đứng, dài tay, có đường xẻ và đính khuy. Có hai túi có nắp phía trước. Phối chi tiết đai cài khuy phía sau. Cài phía trước bằng khuy.	789000	100	36f08100-d8ea-42a0-8c4e-c9f20b45ed26	https://static.zara.net/assets/public/1366/ac2e/104a48c4bbf8/394d2d730174/02722172700-p/02722172700-p.jpg?ts=1775058838306&w=1024	t	t	2026-05-06 07:11:07.14542+00	4.5	0	0	ao-khoac-blazer-vai-pha-linen-zw-collection	\N	\N	GUA Maison	unisex	{}	\N	\N	\N	{}
f8e05505-a89b-4188-a173-90b4c6db1f09	Quần nỉ ống rộng DOUBLE WAIST vải chân cua phối dây rút	1. CHI TIẾT\r\n\r\nTên sản phẩm: Quần nỉ ống rộng DOUBLE WAIST vải chân cua phối dây rút\r\n\r\nChất liệu: Nỉ chân cua, định lượng 400gsm\r\n\r\nThiết kế: ống rộng, streetwear, năng động\r\n\r\n\r\n\r\n2. HƯỚNG DẪN GIẶT VÀ BẢO QUẢN\r\n\r\n\r\n\r\n\r\n3. CAM KẾT THƯƠNG HIỆU\r\n\r\nBAD CHOICES cam kết 100% sản phẩm là ảnh thật shop tự chụp, quý khách hoàn toàn yên tâm khi mua và sử dụng những items đặc sắc tại đây. Brand không đồng ý mọi hành vi sao chép, vi phạm bản quyền hình ảnh.\r\n\r\nThời gian ship chỉ từ 2-3 ngày ở nội thành HCM và 4-5 ngày ở tỉnh thành khác (sẽ linh động nhanh/chậm hơn tùy theo thời gian hàng dự kiến của sàn thương mại điện tử).\r\n\r\n\r\n\r\n4. CHÍNH SÁCH HỖ TRỢ SAU KHI MUA HÀNG\r\n\r\nĐể đảm bảo quyền lợi cho khách hàng cũng như tránh kẻ gian xin quý khách lúc nhận hàng quay lại video khi khui kiện hàng. \r\n\r\nShop hỗ trợ cho các vấn đề của đơn hàng trong vòng 07 ngày sau khi khách nhận hàng theo quy định hiện hành của sàn khi có đầy đủ hình ảnh/video kèm theo. Khách hàng liên hệ phần chat để được nhân viên chăm sóc khách hàng hướng dẫn và hỗ trợ nhanh chóng.	290000	30	18ce9ffd-9078-4174-a8a1-11c1a3d217b9	https://down-vn.img.susercontent.com/file/vn-11134207-820l4-meifryxnonice5.webp	t	t	2026-05-06 08:48:11.299631+00	4.5	0	0	quan-ni-ong-rong-double-waist-vai-chan-cua-phoi-day-rut	\N	\N	GUA Maison	unisex	{}	\N	\N	\N	{}
33333333-3333-3333-3333-333333333333	Quần Jogger GUA Navy	Quần jogger cotton co giãn, cạp chun tiện lợi. Phù hợp cả mặc ở nhà lẫn ra đường.	450000	35	\N	https://images.unsplash.com/photo-1542272604-787c3835535d?w=600	f	f	2026-05-03 01:31:58.35934+00	4.5	0	0	quan-jogger-gua-navy	\N	\N	GUA Maison	men	{}	2026-05-07 10:13:57.166242+00	\N	\N	{}
55555555-5555-5555-5555-555555555555	Áo Polo GUA Kem	Áo polo pique cao cấp, form slim-fit thanh lịch. Phù hợp đi làm và dạo phố cuối tuần.	420000	45	\N	https://images.unsplash.com/photo-1586363104862-3a5e2ab60d99?w=600	f	f	2026-05-03 01:31:58.35934+00	4.5	0	0	ao-polo-gua-kem	\N	\N	GUA Maison	men	\N	2026-05-07 10:14:13.713368+00	\N	\N	{}
11111111-1111-1111-1111-111111111111	Áo Thun Essential GUA Đen	Áo thun basic form rộng, chất liệu cotton 100% cao cấp. Thiết kế tối giản mang DNA của GUA Maison.	350000	73	\N	https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=600	f	f	2026-05-03 01:31:58.35934+00	4.5	0	0	ao-thun-essential-gua-den	\N	\N	GUA Maison	unisex	{}	2026-05-07 10:14:18.977366+00	\N	\N	{}
abb92d0f-3737-44e7-9f6a-10b5892b273a	Quần short đùi caro form ngắn mạc lưng đỏ	Tên sản phẩm: Quần short đùi caro form ngắn mạc lưng đỏ\r\n\r\nChất liệu: Cotton sọc\r\n\r\nThiết kế: form ngắn, mặc dưới rốn	100000	38	36f08100-d8ea-42a0-8c4e-c9f20b45ed26	https://down-vn.img.susercontent.com/file/vn-11134207-820l4-mgq5u3k0lrt656.webp	t	t	2026-05-07 06:44:07.22488+00	4.5	0	0	quan-short-dui-caro-form-ngan-mac-lung-do	\N	\N	GUA Maison	unisex	{}	\N	\N	\N	{}
6538dbcf-35ea-45f0-a4d8-8ec3a2439768	Quần Short Jean Đính Cúc Heaven Sent Wash Ống Rộng	Thông tin sản phẩm\r\n\r\n- Chất liệu: Jean\r\n\r\n- Hình thêu logo HeavenSent\r\n\r\nHướng dẫn sử dụng sản phẩm HEAVEN SENT:\r\n\r\n- Giặt ở nhiệt độ bình thường, với đồ có màu tương tự.\r\n\r\n- Không dùng hóa chất tẩy.\r\n\r\n- Hạn chế sử dụng máy sấy và ủi (nếu có) thì ở nhiệt độ thích hợp.\r\n\r\nChính sách bảo hành:\r\n\r\n– Miễn phí đổi hàng cho khách mua ở HEAVEN SENT trong trường hợp bị lỗi từ nhà sản xuất, giao nhầm hàng, bị hư hỏng \r\n\r\ntrong quá trình vận chuyển hàng.\r\n\r\n– Sản phẩm còn mới nguyên tem, tags và mang theo hoá đơn mua hàng, sản phẩm chưa giặt và không dơ bẩn, hư hỏng bởi những tác nhân bên ngoài cửa hàng sau khi mua hàng.\r\n\r\n	235000	240	36f08100-d8ea-42a0-8c4e-c9f20b45ed26	https://down-vn.img.susercontent.com/file/vn-11134207-81ztc-ml5wuamm2qdp41.webp	t	t	2026-05-07 06:47:31.778525+00	4.5	0	0	quan-short-jean-dinh-cuc-heaven-sent-wash-ong-rong	\N	\N	GUA Maison	unisex	{}	\N	\N	\N	{}
00237cc4-4c67-4074-846c-8724b36144c5	Áo Thun Baby Tee Raglan Vải Borip Breaking New	Áo Thun Baby Tee Raglan Vải Borip Breaking New - HS_TS013\r\n\r\nThông tin sản phẩm\r\n\r\nChất liệu: Borip Cotton\r\n\r\nForm: Baby Tee\r\n\r\nMàu: Vàng / Xanh\r\n\r\nThiết kế áo thun unisex với form boxy, chất liệu cotton mềm mại, phù hợp với mọi phong cách. Áo thun này là lựa chọn lý tưởng cho những ai yêu thích sự thoải mái và phong cách đơn giản.\r\n\r\nHướng dẫn sử dụng\r\n\r\nGiặt ở nhiệt độ bình thường, cùng đồ có màu tương tự.\r\n\r\nKhông dùng hóa chất tẩy.\r\n\r\nHạn chế sử dụng máy sấy và ủi ở nhiệt độ thích hợp.\r\n\r\nChăm sóc đúng cách giúp áo thun luôn bền đẹp. Hãy tuân thủ hướng dẫn để giữ áo thun như mới.\r\n\r\nChính sách bảo hành\r\n\r\nMiễn phí đổi hàng nếu lỗi sản xuất, giao nhầm hoặc hư hỏng trong vận chuyển. Sản phẩm phải còn nguyên tem, tags và hóa đơn. Không dơ bẩn do tác nhân bên ngoài cửa hàng.	189000	80	36f08100-d8ea-42a0-8c4e-c9f20b45ed26	https://down-vn.img.susercontent.com/file/vn-11134207-81ztc-mnuy30h1ys5f7a.webp	t	t	2026-05-07 06:51:09.419056+00	4.5	0	0	ao-thun-baby-tee-raglan-vai-borip-breaking-new	\N	\N	GUA Maison	women	{}	\N	\N	\N	{}
3a2c99a1-6932-43b7-858f-0fc1789a85e7	Áo thun trơn GUAMAISON Basic form Boxy vải premium Cotton	+ THÔNG TIN SẢN PHẨM: Áo thun trơn MME premium cotton\r\n\r\n- Chất liệu: Vải Premium Cotton, 250gsm.\r\n- Form boxy.\r\n- Phù hợp: Mang hàng ngày cho mọi dịp nhu cầu.	159000	45	03b1c590-5a48-42ad-9cdf-312aa80baca7	https://down-vn.img.susercontent.com/file/vn-11134207-7ra0g-m9l9ts4c2o7u8c@resize_w900_nl.webp	t	t	2026-05-07 16:10:51.970553+00	4.5	0	0	ao-thun-tron-GUAMAISON-basic-form-boxy-vai-premium-cotton	\N	\N	GUA Maison	unisex	{}	\N	\N	\N	{}
6e5dbb16-1ab5-4c6c-8828-aa0af77bb7d7	Quần Basic Shorts GUAMAISON form trên gối chất liệu nỉ 2 da mịn cao cấp	+ THÔNG TIN SẢN PHẨM: Quần Basic Shorts GUAMAISON nỉ 2 da\r\n\r\n\r\n\r\n- Chất liệu: Vải nỉ bông.\r\n\r\n- Màu: Đen | Xám Trắng\r\n\r\n- Phù hợp: Mặc ngủ, mặc ở nhà, mặc đi chơi, mặc đi thể thao,...	199000	28	baf050ba-30a9-4c39-8a05-b64a2f59bbd6	https://down-vn.img.susercontent.com/file/vn-11134207-7ras8-mb55i8sd9q6v10.webp	t	t	2026-05-07 16:05:48.341571+00	4.5	0	0	quan-basic-shorts-GUAMAISON-form-tren-goi-chat-lieu-ni-2-da-min-cao-cap	\N	\N	GUA Maison	unisex	{}	\N	\N	\N	{}
9943a8c0-dc51-4a49-918c-d56aa08d5f81	Áo Polo Kẻ WENKO Boxy Cotton Ngắn Tay Kẻ unisex nam nữ PK05	Thiết Kế Boxy\r\n\r\nÁo Polo Kẻ WENKO có thiết kế boxy, tạo nên phong cách thời trang thoải mái. 💯 Đây là lựa chọn lý tưởng cho những ai yêu thích sự thoải mái trong thời trang hàng ngày.\r\n\r\nChất Liệu Cotton\r\n\r\nSản phẩm được làm từ chất liệu cotton, mang lại cảm giác mềm mại khi mặc. 🌿 Chất liệu này đảm bảo sự thoải mái và dễ chịu khi sử dụng.\r\n\r\nÁo Polo Ngắn Tay\r\n\r\nThiết kế ngắn tay, phù hợp cho cả nam và nữ. 📏 Áo Polo Kẻ WENKO là lựa chọn đa dạng cho cả nam và nữ.\r\n\r\nUnisex\r\n\r\nSản phẩm phù hợp cho cả nam và nữ, đa dạng lựa chọn. 🌟 Bạn có thể chọn áo này cho bất kỳ ai trong gia đình.\r\n\r\nThông Tin Sản Phẩm\r\n\r\nMã sản phẩm: PK05. 🏷️\r\n\r\nLoại áo: Áo polo kẻ, thiết kế boxy. 🎨\r\n\r\nChất liệu: Cotton. 🌸\r\n\r\nĐừng bỏ lỡ cơ hội sở hữu sản phẩm Áo Polo Kẻ WENKO. Đặt hàng ngay hôm nay! 🛒	179000	33	03b1c590-5a48-42ad-9cdf-312aa80baca7	https://down-vn.img.susercontent.com/file/vn-11134207-820l4-mj9w5s5c5yww80.webp	f	t	2026-05-07 16:13:56.430319+00	4.5	0	0	ao-polo-ke-wenko-boxy-cotton-ngan-tay-ke-unisex-nam-nu-pk05	\N	\N	GUA Maison	unisex	{}	\N	\N	\N	{}
1cf9e9ff-f61a-472f-9d64-f8350dc55a85	Áo Thun Local Brand VIBESTU " Service " Form Big Boxy Unisex 250Gsm Cotton	Áo Thun Local Brand VIBESTU Form Big Boxy Unisex 250Gsm Cotton\r\n\r\nMÔ TẢ SẢN PHẨM ÁO THUN LOCAL BRAND VIBESTU: \r\n\r\n\r\n\r\n- Chất liệu: 100% cotton, định lượng 250 gsm\r\n\r\n- Họa tiết:  In cao cấp \r\n\r\n- Màu: Đen , Trắng,  Đỏ, Đen\r\n\r\n- Form dáng: Big Boxy -  form áo rộng, áo unisex phù hợp cho cả nam và nữ.\r\n\r\n- Thiết kế và sản xuất bởi VIBESTU\r\n\r\n\r\n\r\nBẢNG SIZE\r\n\r\n\r\n\r\n- Size M: Chiều cao từ < 1m65, cân nặng từ <65kg\r\n\r\n- Size L: Chiều cao từ 1m65 - 1m75, cân nặng từ 65 - 75kg\r\n\r\n- Size XL: Chiều cao từ > 1m75, cân nặng từ > 75kg\r\n\r\n\r\n\r\nHƯỚNG DẪN SỬ DỤNG ÁO THUN BOXY TRƠN:\r\n\r\n\r\n\r\n- Nên giặt tay để sử dụng áo thun local brand được lâu nhất có thể\r\n\r\n- Nhớ lộn trái áo khi giặt và không giặt ngâm\r\n\r\n- Có thể giặt máy\r\n\r\n- Không sử dụng thuốc tẩy\r\n\r\n- Khi phơi lộn trái và không phơi trực tiếp dưới ánh nắng mặt trời\r\n\r\n\r\n\r\nCHÍNH SÁCH ĐỔI TRẢ KHI MUA  ÁO THUN UNISEX TẠI VIBESTU\r\n\r\n\r\n\r\nĐiều kiện đổi trả\r\n\r\n-  Hỗ trợ đổi sản phẩm trong vòng 7 ngày kể từ khi nhận hàng\r\n\r\n-  Liên hệ với VIBESTU nếu sản phẩm có vấn đề lỗi từ nhà sản xuất, giao nhầm hàng, bị hư hỏng trong quá trình vận chuyển. VIBESTU hỗ trợ toàn bộ phí ship. \r\n\r\n- Đối với các sản phẩm đổi do nhu cầu hoặc size các bạn vui lòng thanh phí ship. VIBESTU sẽ hỗ trợ đổi sản phẩm. \r\n\r\n- Kiểm tra gói hàng từ shipper, quay video unbox chi tiết\r\n\r\n\r\n\r\nLưu ý: \r\n\r\n- Áp dụng đổi trả với tất cả các sản phẩm và sản phẩm được đổi phải còn nguyên nhãn mác, trong tình trạng chưa qua sử dụng.\r\n\r\n- Sản phẩm trên ảnh và thực tế có sự chênh lệch màu không đáng kể do điều kiện ánh sáng hoặc màn hình thiết bị hiển thị.\r\n\r\n\r\n\r\nVỀ THƯƠNG HIỆU\r\n\r\n\r\n\r\nVIBESTU là một local brand thời trang giới trẻ được biết đến với những chiếc áo thun, áo polo, áo khoác được thiết kế độc đáo, hiện đại và luôn cập nhật những trend mới. VIBESTU tự hào luôn luôn mang đến sản phẩm chất lượng đến từng đường kim mũi chỉ giúp bạn có thể thoải mái thể hiện phong cách riêng của mình. \r\n\r\n\r\n\r\nVIBESTU CAM KẾT\r\n\r\n- Sản phẩm 100% giống mô tả .Hình ảnh sản phẩm là ảnh thật do shop tự chụp và giữ bản quyền hình ảnh	157989	28	03b1c590-5a48-42ad-9cdf-312aa80baca7	https://down-vn.img.susercontent.com/file/vn-11134207-7ras8-marzarcl5k9k85.webp	f	t	2026-05-07 16:20:58.580172+00	4.5	0	0	ao-thun-local-brand-vibestu-service-form-big-boxy-unisex-250gsm-cotton	\N	\N	GUA Maison	unisex	{}	\N	\N	\N	{}
49f33164-1b39-462d-809e-9912bb9eec88	ALL WIDE STRAIGHT JEANS WHOSE - Quần jeans ống đứng unisex nam nữ Whose Studio	Thông tin sản phẩm \r\n\r\nChất liệu: Jeans cao cấp \r\n\r\nForm: Ống suông siêu to, thùng thình rộng rãi, form thiết kế để cả nam và nữ đều mặc được\r\n\r\nSize: XS S M L XL XXL Quần có màu sắc cực kì trendy xu hướng thời trang mặc từ năm này qua năm nọ không lo lỗi mốt Hỗ trợ đổi size nếu không mặc vừa ! Lưu ý đọc kĩ bảng quy đổi size để tránh việc đổi trả làm mất thời gian của các bạn Cảm ơn quý khách đã tin tưởng ủng hộ, thân ái ❤\r\n\r\n\r\n\r\n\r\n\r\n* Bảng size chỉ mang tính chất tham khảo dựa trên tỷ lệ cơ thể chuẩn, khách hoàn toàn có thể chọn lên hoặc xuống size tuỳ thuộc vào sở thích và form dáng của mình, khách có thể inbox trước với shop để được tư vấn chính xác hơn.\r\n\r\n\r\n\r\nHướng dẫn sử dụng:\r\n\r\n-Lần đầu nên giặt tay, giặt riêng\r\n\r\n-Khi phơi lộn trái sp, không ngâm\r\n\r\n-Không dùng thuốc tẩy\r\n\r\n\r\n\r\nSHOP CAM KẾT\r\n\r\n-Sản phẩm 100% là ảnh thật do mẫu bên shop tự chụp\r\n\r\n-Sản phẩm được kiểm tra kỹ lưỡng trước kho giao, và tư vấn nhiệt tình trước khi gói hàng cho khách\r\n\r\n-Hoàn tiền nếu mẫu sai với mô tả\r\n\r\n-Chấp nhận đổi hàng khi không vừa size\r\n\r\n-Hỗ trợ đổi trả theo quy định shopee\r\n\r\n\r\n\r\nLưu ý: Khách nhận hàng gặp bất kì vấn đề nào liên hệ ngay lại với shop, bên mình phản hồi sớm nhất có thể, đừng vội đánh giá 1 sao nhé\r\n\r\n	189000	54	03b1c590-5a48-42ad-9cdf-312aa80baca7	https://down-vn.img.susercontent.com/file/vn-11134207-820l4-mhbnngbz09ovce.webp	f	t	2026-05-07 16:26:04.731746+00	4.5	0	0	all-wide-straight-jeans-whose-quan-jeans-ong-dung-unisex-nam-nu-whose-studio	\N	\N	GUA Maison	unisex	{}	\N	\N	\N	{}
\.


--
-- Data for Name: return_requests; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.return_requests (id, order_id, user_id, reason, image_url, requested_at, status, reviewed_by, reviewed_at, admin_note, refunded_at, refund_amount) FROM stdin;
\.


--
-- Data for Name: role_permissions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.role_permissions (role_id, permission_id) FROM stdin;
\.


--
-- Data for Name: roles; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.roles (id, tenant_id, parent_id, name, description, is_active, deleted_at, created_at) FROM stdin;
4	\N	\N	customer	Khách hàng mua sắm	t	\N	2026-05-06 03:47:48.654836+00
7	\N	\N	admin	Quản trị viên hệ thống	t	\N	2026-05-06 07:03:28.723842+00
\.


--
-- Data for Name: shipment_events; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.shipment_events (id, shipment_id, status, description, location, raw_data, created_at) FROM stdin;
08c5460a-6e01-4a9b-99e6-5b64d1eb3a7b	f86f62f6-6080-438f-b710-d3ddc09a8f76	pending	Khởi tạo dữ liệu vận chuyển, chờ xử lý.		{}	2026-05-05 07:49:00.652864+00
b75907b2-5d17-4d02-aa1b-dd1f245f74c5	344404bf-db60-404e-a4cc-c714f57d4cf1	pending	Khởi tạo dữ liệu vận chuyển, chờ xử lý.		{}	2026-05-05 07:49:08.250737+00
887cae25-6b65-4383-919a-56b995909eca	5e82483b-a8f7-4711-b975-7e595b845a78	pending	Khởi tạo dữ liệu vận chuyển, chờ xử lý.		{}	2026-05-05 07:58:35.208089+00
eb057f8a-3118-4017-b5ea-5bfb8f2a6c5f	5e82483b-a8f7-4711-b975-7e595b845a78	waiting_pickup	Đã tạo vận đơn thành công qua MOCK. Đang chờ bưu tá lấy hàng.		{"status": "Ready to pick", "message": "Mock Order Created", "tracking_number": "MOCK-373204"}	2026-05-05 07:58:35.932657+00
ddb38967-96e1-4d82-b811-2caf762d6f0a	5e82483b-a8f7-4711-b975-7e595b845a78	returned	Giao hàng thất bại: Khách hàng từ chối nhận hàng. Đang chuyển hoàn về kho GUA.	Bưu cục phát Quận 1	{"Status": "return", "OrderCode": "MOCK-373204", "Warehouse": "Bưu cục phát Quận 1", "Description": "Giao hàng thất bại: Khách hàng từ chối nhận hàng. Đang chuyển hoàn về kho GUA."}	2026-05-05 12:16:19.403028+00
f3c19283-2def-4dd2-bc86-0f693b2a8225	0ba792a2-d7ef-42fc-807f-2a15cd04b427	pending	Khởi tạo dữ liệu vận chuyển, chờ xử lý.		{}	2026-05-05 14:12:13.915519+00
5cb63be2-5716-4a29-b8ef-1c7a858ab85d	0ba792a2-d7ef-42fc-807f-2a15cd04b427	waiting_pickup	Đã tạo vận đơn thành công qua MOCK. Đang chờ bưu tá lấy hàng.		{"status": "Ready to pick", "message": "Mock Order Created", "tracking_number": "MOCK-960301"}	2026-05-05 14:12:14.629667+00
d6f72794-2ee2-4e8e-9fd7-0a6587ccf9c1	0ba792a2-d7ef-42fc-807f-2a15cd04b427	delivered	Giao hàng thành công: Người nhận đã nhận kiện hàng an toàn.	Bưu cục phát Quận 1	{"Status": "delivered", "OrderCode": "MOCK-960301", "Warehouse": "Bưu cục phát Quận 1", "Description": "Giao hàng thành công: Người nhận đã nhận kiện hàng an toàn."}	2026-05-05 14:12:50.68368+00
35726e3f-1464-4ef4-89f4-70a2cad936bc	eecf5688-9fed-42bc-8a80-8f71b746799e	pending	Khởi tạo dữ liệu vận chuyển, chờ xử lý.		{}	2026-05-06 02:17:32.811974+00
c5010ab6-590b-4c44-9918-703b7f8c2a1f	eecf5688-9fed-42bc-8a80-8f71b746799e	waiting_pickup	Đã tạo vận đơn thành công qua SELF_SHIP. Đang chờ bưu tá lấy hàng.		{"type": "self_ship", "message": "Vận đơn nội bộ đã tạo bởi GUA Maison", "recipient": {"name": "Khoa lê", "phone": "0383196830", "address": "123 Lạc long quan, 124 Lạc long quan, Huyện Ba Bể, Tỉnh Bắc Kạn"}, "instructions": "Nhân viên giao hàng cần cập nhật trạng thái thủ công trên trang quản lý đơn hàng khi: (1) Đã lấy hàng, (2) Đang giao, (3) Giao thành công / Thất bại.", "tracking_code": "GUA-20260506-8IVNVM"}	2026-05-06 02:17:33.434917+00
53ece985-ef4c-433d-9529-00ded94c7689	58e6d5a2-d2ea-4ca1-a99a-0d77bef84a68	pending	Khởi tạo dữ liệu vận chuyển, chờ xử lý.		{}	2026-05-06 07:12:43.569434+00
8b253bbf-0e08-47e9-98f4-0f523309aeaa	58e6d5a2-d2ea-4ca1-a99a-0d77bef84a68	failed	Lỗi API GHN: Unknown API Error		{"code": 401, "error": "GHN chưa được cấu hình. Vui lòng nhập Token và Shop ID trong trang Đơn vị vận chuyển."}	2026-05-06 07:12:44.215145+00
0185d0c1-16d5-4491-bf8b-016e5b51b58a	385ffecc-e65a-4d49-9c67-020b616d134b	pending	Khởi tạo dữ liệu vận chuyển, chờ xử lý.		{}	2026-05-06 07:12:49.094122+00
c2a4e183-8111-442e-ab3f-27c8222ac780	385ffecc-e65a-4d49-9c67-020b616d134b	waiting_pickup	Đã tạo vận đơn thành công qua MOCK. Đang chờ bưu tá lấy hàng.		{"status": "Ready to pick", "message": "Mock Order Created", "tracking_number": "MOCK-135341"}	2026-05-06 07:12:49.73063+00
be5fb288-9090-4b94-af74-607bdd1e6f57	50a34692-85df-4b74-8e50-8d3bdf7daaaf	pending	Khởi tạo dữ liệu vận chuyển, chờ xử lý.		{}	2026-05-08 14:11:55.257499+00
120e5a52-2413-4c7a-ab2a-6fe66e1b11c5	50a34692-85df-4b74-8e50-8d3bdf7daaaf	waiting_pickup	Đã tạo vận đơn thành công qua MOCK. Đang chờ bưu tá lấy hàng.		{"status": "Ready to pick", "message": "Mock Order Created", "tracking_number": "MOCK-443049"}	2026-05-08 14:11:55.916299+00
2a3f94bc-3d3f-4746-a4f6-7d8b680d41e8	50a34692-85df-4b74-8e50-8d3bdf7daaaf	delivered	Giao hàng thành công: Người nhận đã nhận kiện hàng an toàn.	Bưu cục phát Quận 1	{"Status": "delivered", "OrderCode": "MOCK-443049", "Warehouse": "Bưu cục phát Quận 1", "Description": "Giao hàng thành công: Người nhận đã nhận kiện hàng an toàn."}	2026-05-08 14:12:37.70206+00
\.


--
-- Data for Name: shipments; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.shipments (id, order_id, provider, tracking_code, shipping_fee, actual_shipping_fee, cod_amount, package_index, weight_g, dimensions_json, recipient_name, recipient_phone, recipient_address, recipient_ward_code, recipient_district_id, recipient_province_id, status, delayed, expected_delivery_at, shipped_at, delivered_at, raw_response, created_at, updated_at, delivery_attempts, failed_reason) FROM stdin;
f86f62f6-6080-438f-b710-d3ddc09a8f76	b7105c04-40df-4012-b5db-ec309c6865f5	mock	\N	0.00	0.00	1580000.00	1	500	{"h": 10, "l": 20, "w": 15}	Lê Trần Đăng Khoa	0383196830	286 Lạc Long Quân, 286 Lạc Long Quân	\N	\N	\N	pending	f	\N	\N	\N	{}	2026-05-05 07:49:00.49015+00	2026-05-05 07:49:00.806757+00	0	\N
344404bf-db60-404e-a4cc-c714f57d4cf1	b7105c04-40df-4012-b5db-ec309c6865f5	self_ship	\N	0.00	0.00	1580000.00	1	500	{"h": 10, "l": 20, "w": 15}	Lê Trần Đăng Khoa	0383196830	286 Lạc Long Quân, 286 Lạc Long Quân	\N	\N	\N	pending	f	\N	\N	\N	{}	2026-05-05 07:49:08.08193+00	2026-05-05 07:49:08.40846+00	0	\N
58e6d5a2-d2ea-4ca1-a99a-0d77bef84a68	82afa8b2-c274-4eec-8d91-3c691318f59b	ghn	\N	30000.00	0.00	0.00	1	500	{"h": 10, "l": 20, "w": 15}	Khoa lê	0383196830	123 Lạc long quan, 124 Lạc long quan, Huyện Ba Bể, Tỉnh Bắc Kạn		\N	\N	failed	f	\N	\N	\N	{}	2026-05-06 07:12:43.38851+00	2026-05-06 07:12:44.393404+00	0	\N
5e82483b-a8f7-4711-b975-7e595b845a78	b7105c04-40df-4012-b5db-ec309c6865f5	mock	MOCK-373204	0.00	0.00	1580000.00	1	500	{"h": 10, "l": 20, "w": 15}	Lê Trần Đăng Khoa	0383196830	286 Lạc Long Quân, 286 Lạc Long Quân, Huyện Cờ Đỏ, Thành phố Cần Thơ		\N	\N	returned	f	\N	2026-05-05 14:58:36.346973+00	\N	{"status": "Ready to pick", "message": "Mock Order Created", "tracking_number": "MOCK-373204"}	2026-05-05 07:58:35.012985+00	2026-05-05 12:16:19.598006+00	0	\N
0ba792a2-d7ef-42fc-807f-2a15cd04b427	552046cb-2fc6-4571-bab9-dc60926c50a8	mock	MOCK-960301	45000.00	0.00	395000.00	1	500	{"h": 10, "l": 20, "w": 15}	Lê Trần Đăng Khoa	0383196830	286 Lạc Long Quân, 286 Lạc Long Quân, Huyện Cờ Đỏ, Thành phố Cần Thơ		\N	\N	delivered	f	\N	2026-05-05 21:12:16.019796+00	2026-05-05 14:12:52.446233+00	{"status": "Ready to pick", "message": "Mock Order Created", "tracking_number": "MOCK-960301"}	2026-05-05 14:12:13.710062+00	2026-05-05 14:12:50.908443+00	0	\N
385ffecc-e65a-4d49-9c67-020b616d134b	82afa8b2-c274-4eec-8d91-3c691318f59b	mock	MOCK-135341	30000.00	0.00	0.00	1	500	{"h": 10, "l": 20, "w": 15}	Khoa lê	0383196830	123 Lạc long quan, 124 Lạc long quan, Huyện Ba Bể, Tỉnh Bắc Kạn		\N	\N	waiting_pickup	f	\N	2026-05-06 14:12:51.929614+00	\N	{"status": "Ready to pick", "message": "Mock Order Created", "tracking_number": "MOCK-135341"}	2026-05-06 07:12:48.927477+00	2026-05-06 07:12:49.88667+00	0	\N
eecf5688-9fed-42bc-8a80-8f71b746799e	8b03b65f-1d28-4c0f-b975-c748546f037a	self_ship	GUA-20260506-8IVNVM	30000.00	0.00	0.00	1	500	{"h": 10, "l": 20, "w": 15}	Khoa lê	0383196830	123 Lạc long quan, 124 Lạc long quan, Huyện Ba Bể, Tỉnh Bắc Kạn		\N	\N	waiting_pickup	f	\N	2026-05-06 09:17:36.071533+00	\N	{"type": "self_ship", "message": "Vận đơn nội bộ đã tạo bởi GUA Maison", "recipient": {"name": "Khoa lê", "phone": "0383196830", "address": "123 Lạc long quan, 124 Lạc long quan, Huyện Ba Bể, Tỉnh Bắc Kạn"}, "instructions": "Nhân viên giao hàng cần cập nhật trạng thái thủ công trên trang quản lý đơn hàng khi: (1) Đã lấy hàng, (2) Đang giao, (3) Giao thành công / Thất bại.", "tracking_code": "GUA-20260506-8IVNVM"}	2026-05-06 02:17:32.638032+00	2026-05-06 02:17:33.591884+00	0	\N
50a34692-85df-4b74-8e50-8d3bdf7daaaf	dc1c7753-cd60-40e5-9e00-ffcdcda165f3	mock	MOCK-443049	30000.00	0.00	219000.00	1	500	{"h": 10, "l": 20, "w": 15}	Khoa lê	0383196830	123 Lạc long quan, 124 Lạc long quan, Huyện Ba Bể, Tỉnh Bắc Kạn		\N	\N	delivered	f	\N	2026-05-08 21:11:56.076624+00	2026-05-08 14:12:38.235814+00	{"status": "Ready to pick", "message": "Mock Order Created", "tracking_number": "MOCK-443049"}	2026-05-08 14:11:55.086736+00	2026-05-08 14:12:37.905652+00	0	\N
\.


--
-- Data for Name: shipping_configs; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.shipping_configs (id, freeship_threshold, hcm_fee, hn_fee, default_fee, updated_at) FROM stdin;
1	2000000.00	30000.00	40000.00	50000.00	2026-05-05 06:40:02.365745+00
\.


--
-- Data for Name: shipping_providers; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.shipping_providers (id, name, description, is_active, config, icon, sort_order, created_at) FROM stdin;
ghn	Giao Hàng Nhanh (GHN)	Hệ thống vận chuyển phủ sóng toàn quốc.	t	{"token": "", "shop_id": ""}	fa-truck-fast	1	2026-05-04 03:19:09.881515+00
self_ship	Tự giao hàng (Nội bộ)	Nhân viên shop trực tiếp đi giao.	t	{}	fa-motorcycle	2	2026-05-04 03:19:09.881515+00
mock	Môi trường Giả lập (Test)	Dùng để thử nghiệm luồng vận hành.	t	{}	fa-flask-vial	3	2026-05-04 03:19:09.881515+00
\.


--
-- Data for Name: system_settings; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.system_settings (id, general, storefront, integrations, updated_at, shipping_rules) FROM stdin;
1	{"hotline": "0901234567", "shop_name": "GUA Maison"}	{}	{}	2026-05-05 07:07:13.252365+00	{"rules": [{"fee": 55000, "warning": "có bão ", "province": "Cần Thơ"}]}
\.


--
-- Data for Name: tenants; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.tenants (id, name, domain, is_active, created_at) FROM stdin;
\.


--
-- Data for Name: user_addresses; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.user_addresses (id, user_id, full_name, phone, address_line, is_default, created_at, province, district, ward, note) FROM stdin;
95504c6c-e99c-4bfa-b277-5fd74aed3689	85b1983b-178f-4ab1-b8bb-6eda246ad71e	Lê Trần Đăng	0891263517	254, ABC	t	2026-04-29 08:44:08.720373+00	Tỉnh Bắc Kạn	Huyện Bạch Thông	Xã Vũ Muộn	
37d78297-4325-4ef0-abea-ef6efadd659a	1aa70cbe-823c-4877-9344-cf1fdefced30	Lê Trần Đăng Khoa	0383196830	286 Lạc Long Quân, 286 Lạc Long Quân	t	2026-05-02 06:20:26.318127+00	Thành phố Cần Thơ	Huyện Cờ Đỏ	Xã Thới Hưng	
6c2783f3-4957-46f1-b715-9c476e05d25d	5a318635-d758-4b20-99ac-b79d097f0072	Khoa lê	0383196830	123 Lạc long quan, 124 Lạc long quan	t	2026-04-29 09:09:20.75545+00	Tỉnh Bắc Kạn	Huyện Ba Bể	Thị trấn Chợ Rã	
\.


--
-- Data for Name: user_permissions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.user_permissions (user_id, permission_id, is_granted) FROM stdin;
\.


--
-- Data for Name: user_roles; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.user_roles (user_id, role_id, tenant_id) FROM stdin;
54bcef72-5d6d-4e21-bee1-e54e6592de9f	7	\N
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.users (id, email, password_hash, full_name, created_at, phone, is_vip, role) FROM stdin;
1aa70cbe-823c-4877-9344-cf1fdefced30	khoale3@gmail.com	$2b$12$mRk5XdM7W6wBfyRc83eHU.BedRBnUartVR9TmFf/nPGy8H/F9QIdq	Lê Khoa	2026-05-02 06:19:46.854136+00	0383196830	f	customer
5a318635-d758-4b20-99ac-b79d097f0072	khoale30092003@gmail.com	$2b$12$Ok1ur0LQ3AB1r5i0jfLOkeMt8FkaUVuwG11ac5GcrdTqeQRC8lYvS	Lê Khoa	2026-04-22 01:44:35.325365+00	0383196830	f	customer
30983a82-b6b8-4615-b6dd-ee97476851fd	obama@gmail.com	$2b$12$hKUzAvTyygTsebkyFLHb/.c2hl4ZU4KwZQBUAgct.86nbF.BBHPFG	Quách Gia Phú	2026-05-03 02:37:07.910971+00	\N	f	customer
54bcef72-5d6d-4e21-bee1-e54e6592de9f	admin123@gmail.com	$2b$12$gtH/Xo6IIIcBRODGCasjCe3SC7W0Tp.dPnM/pgOZChMkPhR2wgvmS	Super Admin	2026-05-06 07:02:59.394596+00	\N	f	customer
85b1983b-178f-4ab1-b8bb-6eda246ad71e	obama9778@gmail.com	$2b$12$UfdvzbMLbuYhflHLXVKRo.VchpqkYQVqaaLIg5bipGeoA2lP4T1OG	Lê Trần Đăng	2026-04-25 09:48:44.568075+00	01288318892	f	customer
\.


--
-- Data for Name: webhook_logs; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.webhook_logs (id, provider, event_type, payload, status_code, error_message, created_at) FROM stdin;
\.


--
-- Data for Name: schema_migrations; Type: TABLE DATA; Schema: realtime; Owner: -
--

COPY realtime.schema_migrations (version, inserted_at) FROM stdin;
20211116024918	2026-04-21 03:47:35
20211116045059	2026-04-21 03:47:36
20211116050929	2026-04-21 03:47:37
20211116051442	2026-04-21 03:47:38
20211116212300	2026-04-21 03:47:39
20211116213355	2026-04-21 03:47:39
20211116213934	2026-04-21 03:47:40
20211116214523	2026-04-21 03:47:41
20211122062447	2026-04-21 03:47:42
20211124070109	2026-04-21 03:47:42
20211202204204	2026-04-21 03:47:43
20211202204605	2026-04-21 03:47:44
20211210212804	2026-04-21 03:47:46
20211228014915	2026-04-21 03:47:47
20220107221237	2026-04-21 03:47:47
20220228202821	2026-04-21 03:47:48
20220312004840	2026-04-21 03:47:49
20220603231003	2026-04-21 03:47:50
20220603232444	2026-04-21 03:47:51
20220615214548	2026-04-21 03:47:52
20220712093339	2026-04-21 03:47:52
20220908172859	2026-04-21 03:47:53
20220916233421	2026-04-21 03:47:54
20230119133233	2026-04-21 03:47:54
20230128025114	2026-04-21 03:47:55
20230128025212	2026-04-21 03:47:56
20230227211149	2026-04-21 03:47:57
20230228184745	2026-04-21 03:47:57
20230308225145	2026-04-21 03:47:58
20230328144023	2026-04-21 03:47:59
20231018144023	2026-04-21 03:47:59
20231204144023	2026-04-21 03:48:01
20231204144024	2026-04-21 03:48:01
20231204144025	2026-04-21 03:48:02
20240108234812	2026-04-21 03:48:03
20240109165339	2026-04-21 03:48:03
20240227174441	2026-04-21 03:48:05
20240311171622	2026-04-21 03:48:06
20240321100241	2026-04-21 03:48:07
20240401105812	2026-04-21 03:48:09
20240418121054	2026-04-21 03:48:10
20240523004032	2026-04-21 03:48:12
20240618124746	2026-04-21 03:48:13
20240801235015	2026-04-21 03:48:14
20240805133720	2026-04-21 03:48:14
20240827160934	2026-04-21 03:48:15
20240919163303	2026-04-21 03:48:16
20240919163305	2026-04-21 03:48:17
20241019105805	2026-04-21 03:48:17
20241030150047	2026-04-21 03:48:20
20241108114728	2026-04-21 03:48:21
20241121104152	2026-04-21 03:48:22
20241130184212	2026-04-21 03:48:23
20241220035512	2026-04-21 03:48:23
20241220123912	2026-04-21 03:48:24
20241224161212	2026-04-21 03:48:25
20250107150512	2026-04-21 03:48:25
20250110162412	2026-04-21 03:48:26
20250123174212	2026-04-21 03:48:27
20250128220012	2026-04-21 03:48:27
20250506224012	2026-04-21 03:48:28
20250523164012	2026-04-21 03:48:29
20250714121412	2026-04-21 03:48:29
20250905041441	2026-04-21 03:48:30
20251103001201	2026-04-21 03:48:31
20251120212548	2026-04-21 03:48:32
20251120215549	2026-04-21 03:48:32
20260218120000	2026-04-21 03:48:33
20260326120000	2026-04-21 03:48:34
\.


--
-- Data for Name: subscription; Type: TABLE DATA; Schema: realtime; Owner: -
--

COPY realtime.subscription (id, subscription_id, entity, filters, claims, created_at, action_filter) FROM stdin;
\.


--
-- Data for Name: buckets; Type: TABLE DATA; Schema: storage; Owner: -
--

COPY storage.buckets (id, name, owner, created_at, updated_at, public, avif_autodetection, file_size_limit, allowed_mime_types, owner_id, type) FROM stdin;
product-images	product-images	\N	2026-04-27 01:41:57.591275+00	2026-04-27 01:41:57.591275+00	t	f	\N	\N	\N	STANDARD
\.


--
-- Data for Name: buckets_analytics; Type: TABLE DATA; Schema: storage; Owner: -
--

COPY storage.buckets_analytics (name, type, format, created_at, updated_at, id, deleted_at) FROM stdin;
\.


--
-- Data for Name: buckets_vectors; Type: TABLE DATA; Schema: storage; Owner: -
--

COPY storage.buckets_vectors (id, type, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: migrations; Type: TABLE DATA; Schema: storage; Owner: -
--

COPY storage.migrations (id, name, hash, executed_at) FROM stdin;
0	create-migrations-table	e18db593bcde2aca2a408c4d1100f6abba2195df	2026-04-21 03:47:52.423937
1	initialmigration	6ab16121fbaa08bbd11b712d05f358f9b555d777	2026-04-21 03:47:52.43534
2	storage-schema	f6a1fa2c93cbcd16d4e487b362e45fca157a8dbd	2026-04-21 03:47:52.443084
3	pathtoken-column	2cb1b0004b817b29d5b0a971af16bafeede4b70d	2026-04-21 03:47:52.460624
4	add-migrations-rls	427c5b63fe1c5937495d9c635c263ee7a5905058	2026-04-21 03:47:52.47012
5	add-size-functions	79e081a1455b63666c1294a440f8ad4b1e6a7f84	2026-04-21 03:47:52.476044
6	change-column-name-in-get-size	ded78e2f1b5d7e616117897e6443a925965b30d2	2026-04-21 03:47:52.483433
7	add-rls-to-buckets	e7e7f86adbc51049f341dfe8d30256c1abca17aa	2026-04-21 03:47:52.490107
8	add-public-to-buckets	fd670db39ed65f9d08b01db09d6202503ca2bab3	2026-04-21 03:47:52.496547
9	fix-search-function	af597a1b590c70519b464a4ab3be54490712796b	2026-04-21 03:47:52.502653
10	search-files-search-function	b595f05e92f7e91211af1bbfe9c6a13bb3391e16	2026-04-21 03:47:52.509138
11	add-trigger-to-auto-update-updated_at-column	7425bdb14366d1739fa8a18c83100636d74dcaa2	2026-04-21 03:47:52.515503
12	add-automatic-avif-detection-flag	8e92e1266eb29518b6a4c5313ab8f29dd0d08df9	2026-04-21 03:47:52.522313
13	add-bucket-custom-limits	cce962054138135cd9a8c4bcd531598684b25e7d	2026-04-21 03:47:52.528579
14	use-bytes-for-max-size	941c41b346f9802b411f06f30e972ad4744dad27	2026-04-21 03:47:52.535444
15	add-can-insert-object-function	934146bc38ead475f4ef4b555c524ee5d66799e5	2026-04-21 03:47:52.557687
16	add-version	76debf38d3fd07dcfc747ca49096457d95b1221b	2026-04-21 03:47:52.595717
17	drop-owner-foreign-key	f1cbb288f1b7a4c1eb8c38504b80ae2a0153d101	2026-04-21 03:47:52.607666
18	add_owner_id_column_deprecate_owner	e7a511b379110b08e2f214be852c35414749fe66	2026-04-21 03:47:52.625172
19	alter-default-value-objects-id	02e5e22a78626187e00d173dc45f58fa66a4f043	2026-04-21 03:47:52.649553
20	list-objects-with-delimiter	cd694ae708e51ba82bf012bba00caf4f3b6393b7	2026-04-21 03:47:52.684468
21	s3-multipart-uploads	8c804d4a566c40cd1e4cc5b3725a664a9303657f	2026-04-21 03:47:52.707495
22	s3-multipart-uploads-big-ints	9737dc258d2397953c9953d9b86920b8be0cdb73	2026-04-21 03:47:52.722599
23	optimize-search-function	9d7e604cddc4b56a5422dc68c9313f4a1b6f132c	2026-04-21 03:47:52.733966
24	operation-function	8312e37c2bf9e76bbe841aa5fda889206d2bf8aa	2026-04-21 03:47:52.740188
25	custom-metadata	d974c6057c3db1c1f847afa0e291e6165693b990	2026-04-21 03:47:52.74637
26	objects-prefixes	215cabcb7f78121892a5a2037a09fedf9a1ae322	2026-04-21 03:47:52.752569
27	search-v2	859ba38092ac96eb3964d83bf53ccc0b141663a6	2026-04-21 03:47:52.758245
28	object-bucket-name-sorting	c73a2b5b5d4041e39705814fd3a1b95502d38ce4	2026-04-21 03:47:52.763837
29	create-prefixes	ad2c1207f76703d11a9f9007f821620017a66c21	2026-04-21 03:47:52.76949
30	update-object-levels	2be814ff05c8252fdfdc7cfb4b7f5c7e17f0bed6	2026-04-21 03:47:52.775001
31	objects-level-index	b40367c14c3440ec75f19bbce2d71e914ddd3da0	2026-04-21 03:47:52.780705
32	backward-compatible-index-on-objects	e0c37182b0f7aee3efd823298fb3c76f1042c0f7	2026-04-21 03:47:52.786499
33	backward-compatible-index-on-prefixes	b480e99ed951e0900f033ec4eb34b5bdcb4e3d49	2026-04-21 03:47:52.792298
34	optimize-search-function-v1	ca80a3dc7bfef894df17108785ce29a7fc8ee456	2026-04-21 03:47:52.798142
35	add-insert-trigger-prefixes	458fe0ffd07ec53f5e3ce9df51bfdf4861929ccc	2026-04-21 03:47:52.803535
36	optimise-existing-functions	6ae5fca6af5c55abe95369cd4f93985d1814ca8f	2026-04-21 03:47:52.80929
37	add-bucket-name-length-trigger	3944135b4e3e8b22d6d4cbb568fe3b0b51df15c1	2026-04-21 03:47:52.815085
38	iceberg-catalog-flag-on-buckets	02716b81ceec9705aed84aa1501657095b32e5c5	2026-04-21 03:47:52.822052
39	add-search-v2-sort-support	6706c5f2928846abee18461279799ad12b279b78	2026-04-21 03:47:52.831898
40	fix-prefix-race-conditions-optimized	7ad69982ae2d372b21f48fc4829ae9752c518f6b	2026-04-21 03:47:52.837689
41	add-object-level-update-trigger	07fcf1a22165849b7a029deed059ffcde08d1ae0	2026-04-21 03:47:52.843571
42	rollback-prefix-triggers	771479077764adc09e2ea2043eb627503c034cd4	2026-04-21 03:47:52.849021
43	fix-object-level	84b35d6caca9d937478ad8a797491f38b8c2979f	2026-04-21 03:47:52.854729
44	vector-bucket-type	99c20c0ffd52bb1ff1f32fb992f3b351e3ef8fb3	2026-04-21 03:47:52.860251
45	vector-buckets	049e27196d77a7cb76497a85afae669d8b230953	2026-04-21 03:47:52.866758
46	buckets-objects-grants	fedeb96d60fefd8e02ab3ded9fbde05632f84aed	2026-04-21 03:47:52.878068
47	iceberg-table-metadata	649df56855c24d8b36dd4cc1aeb8251aa9ad42c2	2026-04-21 03:47:52.883932
48	iceberg-catalog-ids	e0e8b460c609b9999ccd0df9ad14294613eed939	2026-04-21 03:47:52.889829
49	buckets-objects-grants-postgres	072b1195d0d5a2f888af6b2302a1938dd94b8b3d	2026-04-21 03:47:52.905987
50	search-v2-optimised	6323ac4f850aa14e7387eb32102869578b5bd478	2026-04-21 03:47:52.912021
51	index-backward-compatible-search	2ee395d433f76e38bcd3856debaf6e0e5b674011	2026-04-21 03:47:52.928475
52	drop-not-used-indexes-and-functions	5cc44c8696749ac11dd0dc37f2a3802075f3a171	2026-04-21 03:47:52.930968
53	drop-index-lower-name	d0cb18777d9e2a98ebe0bc5cc7a42e57ebe41854	2026-04-21 03:47:52.945191
54	drop-index-object-level	6289e048b1472da17c31a7eba1ded625a6457e67	2026-04-21 03:47:52.950059
55	prevent-direct-deletes	262a4798d5e0f2e7c8970232e03ce8be695d5819	2026-04-21 03:47:52.952372
57	s3-multipart-uploads-metadata	f127886e00d1b374fadbc7c6b31e09336aad5287	2026-04-21 03:47:52.966302
58	operation-ergonomics	00ca5d483b3fe0d522133d9002ccc5df98365120	2026-04-21 03:47:52.972598
56	fix-optimized-search-function	b823ed1e418101032fa01374edc9a436e54e3ed4	2026-04-21 03:47:52.958958
59	drop-unused-functions	38456f13e39691c2bbb4b5151d0d1cdbabd4a8c4	2026-05-06 01:01:50.111881
60	optimize-existing-functions-again	db35e1c91a9201e59f4fef8d972c2f277d68b157	2026-05-06 01:01:50.155407
\.


--
-- Data for Name: objects; Type: TABLE DATA; Schema: storage; Owner: -
--

COPY storage.objects (id, bucket_id, name, owner, created_at, updated_at, last_accessed_at, metadata, version, owner_id, user_metadata) FROM stdin;
\.


--
-- Data for Name: s3_multipart_uploads; Type: TABLE DATA; Schema: storage; Owner: -
--

COPY storage.s3_multipart_uploads (id, in_progress_size, upload_signature, bucket_id, key, version, owner_id, created_at, user_metadata, metadata) FROM stdin;
\.


--
-- Data for Name: s3_multipart_uploads_parts; Type: TABLE DATA; Schema: storage; Owner: -
--

COPY storage.s3_multipart_uploads_parts (id, upload_id, size, part_number, bucket_id, key, etag, owner_id, version, created_at) FROM stdin;
\.


--
-- Data for Name: vector_indexes; Type: TABLE DATA; Schema: storage; Owner: -
--

COPY storage.vector_indexes (id, name, bucket_id, data_type, dimension, distance_metric, metadata_configuration, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: secrets; Type: TABLE DATA; Schema: vault; Owner: -
--

COPY vault.secrets (id, name, description, secret, key_id, nonce, created_at, updated_at) FROM stdin;
\.


--
-- Name: refresh_tokens_id_seq; Type: SEQUENCE SET; Schema: auth; Owner: -
--

SELECT pg_catalog.setval('auth.refresh_tokens_id_seq', 1, false);


--
-- Name: carrier_status_mapping_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.carrier_status_mapping_id_seq', 1, false);


--
-- Name: permission_groups_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.permission_groups_id_seq', 1, false);


--
-- Name: permissions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.permissions_id_seq', 1, false);


--
-- Name: roles_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.roles_id_seq', 7, true);


--
-- Name: subscription_id_seq; Type: SEQUENCE SET; Schema: realtime; Owner: -
--

SELECT pg_catalog.setval('realtime.subscription_id_seq', 1, false);


--
-- Name: mfa_amr_claims amr_id_pk; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.mfa_amr_claims
    ADD CONSTRAINT amr_id_pk PRIMARY KEY (id);


--
-- Name: audit_log_entries audit_log_entries_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.audit_log_entries
    ADD CONSTRAINT audit_log_entries_pkey PRIMARY KEY (id);


--
-- Name: custom_oauth_providers custom_oauth_providers_identifier_key; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.custom_oauth_providers
    ADD CONSTRAINT custom_oauth_providers_identifier_key UNIQUE (identifier);


--
-- Name: custom_oauth_providers custom_oauth_providers_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.custom_oauth_providers
    ADD CONSTRAINT custom_oauth_providers_pkey PRIMARY KEY (id);


--
-- Name: flow_state flow_state_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.flow_state
    ADD CONSTRAINT flow_state_pkey PRIMARY KEY (id);


--
-- Name: identities identities_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.identities
    ADD CONSTRAINT identities_pkey PRIMARY KEY (id);


--
-- Name: identities identities_provider_id_provider_unique; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.identities
    ADD CONSTRAINT identities_provider_id_provider_unique UNIQUE (provider_id, provider);


--
-- Name: instances instances_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.instances
    ADD CONSTRAINT instances_pkey PRIMARY KEY (id);


--
-- Name: mfa_amr_claims mfa_amr_claims_session_id_authentication_method_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.mfa_amr_claims
    ADD CONSTRAINT mfa_amr_claims_session_id_authentication_method_pkey UNIQUE (session_id, authentication_method);


--
-- Name: mfa_challenges mfa_challenges_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.mfa_challenges
    ADD CONSTRAINT mfa_challenges_pkey PRIMARY KEY (id);


--
-- Name: mfa_factors mfa_factors_last_challenged_at_key; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.mfa_factors
    ADD CONSTRAINT mfa_factors_last_challenged_at_key UNIQUE (last_challenged_at);


--
-- Name: mfa_factors mfa_factors_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.mfa_factors
    ADD CONSTRAINT mfa_factors_pkey PRIMARY KEY (id);


--
-- Name: oauth_authorizations oauth_authorizations_authorization_code_key; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.oauth_authorizations
    ADD CONSTRAINT oauth_authorizations_authorization_code_key UNIQUE (authorization_code);


--
-- Name: oauth_authorizations oauth_authorizations_authorization_id_key; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.oauth_authorizations
    ADD CONSTRAINT oauth_authorizations_authorization_id_key UNIQUE (authorization_id);


--
-- Name: oauth_authorizations oauth_authorizations_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.oauth_authorizations
    ADD CONSTRAINT oauth_authorizations_pkey PRIMARY KEY (id);


--
-- Name: oauth_client_states oauth_client_states_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.oauth_client_states
    ADD CONSTRAINT oauth_client_states_pkey PRIMARY KEY (id);


--
-- Name: oauth_clients oauth_clients_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.oauth_clients
    ADD CONSTRAINT oauth_clients_pkey PRIMARY KEY (id);


--
-- Name: oauth_consents oauth_consents_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.oauth_consents
    ADD CONSTRAINT oauth_consents_pkey PRIMARY KEY (id);


--
-- Name: oauth_consents oauth_consents_user_client_unique; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.oauth_consents
    ADD CONSTRAINT oauth_consents_user_client_unique UNIQUE (user_id, client_id);


--
-- Name: one_time_tokens one_time_tokens_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.one_time_tokens
    ADD CONSTRAINT one_time_tokens_pkey PRIMARY KEY (id);


--
-- Name: refresh_tokens refresh_tokens_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.refresh_tokens
    ADD CONSTRAINT refresh_tokens_pkey PRIMARY KEY (id);


--
-- Name: refresh_tokens refresh_tokens_token_unique; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.refresh_tokens
    ADD CONSTRAINT refresh_tokens_token_unique UNIQUE (token);


--
-- Name: saml_providers saml_providers_entity_id_key; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.saml_providers
    ADD CONSTRAINT saml_providers_entity_id_key UNIQUE (entity_id);


--
-- Name: saml_providers saml_providers_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.saml_providers
    ADD CONSTRAINT saml_providers_pkey PRIMARY KEY (id);


--
-- Name: saml_relay_states saml_relay_states_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.saml_relay_states
    ADD CONSTRAINT saml_relay_states_pkey PRIMARY KEY (id);


--
-- Name: schema_migrations schema_migrations_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.schema_migrations
    ADD CONSTRAINT schema_migrations_pkey PRIMARY KEY (version);


--
-- Name: sessions sessions_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.sessions
    ADD CONSTRAINT sessions_pkey PRIMARY KEY (id);


--
-- Name: sso_domains sso_domains_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.sso_domains
    ADD CONSTRAINT sso_domains_pkey PRIMARY KEY (id);


--
-- Name: sso_providers sso_providers_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.sso_providers
    ADD CONSTRAINT sso_providers_pkey PRIMARY KEY (id);


--
-- Name: users users_phone_key; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.users
    ADD CONSTRAINT users_phone_key UNIQUE (phone);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: webauthn_challenges webauthn_challenges_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.webauthn_challenges
    ADD CONSTRAINT webauthn_challenges_pkey PRIMARY KEY (id);


--
-- Name: webauthn_credentials webauthn_credentials_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.webauthn_credentials
    ADD CONSTRAINT webauthn_credentials_pkey PRIMARY KEY (id);


--
-- Name: audit_logs audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_pkey PRIMARY KEY (id);


--
-- Name: brands brands_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.brands
    ADD CONSTRAINT brands_pkey PRIMARY KEY (id);


--
-- Name: brands brands_slug_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.brands
    ADD CONSTRAINT brands_slug_key UNIQUE (slug);


--
-- Name: carrier_status_mapping carrier_status_mapping_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.carrier_status_mapping
    ADD CONSTRAINT carrier_status_mapping_pkey PRIMARY KEY (id);


--
-- Name: carrier_status_mapping carrier_status_mapping_provider_carrier_status_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.carrier_status_mapping
    ADD CONSTRAINT carrier_status_mapping_provider_carrier_status_key UNIQUE (provider, carrier_status);


--
-- Name: cart_items cart_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cart_items
    ADD CONSTRAINT cart_items_pkey PRIMARY KEY (id);


--
-- Name: categories categories_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.categories
    ADD CONSTRAINT categories_pkey PRIMARY KEY (id);


--
-- Name: categories categories_slug_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.categories
    ADD CONSTRAINT categories_slug_key UNIQUE (slug);


--
-- Name: coupon_categories coupon_categories_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coupon_categories
    ADD CONSTRAINT coupon_categories_pkey PRIMARY KEY (coupon_id, category_id);


--
-- Name: coupon_products coupon_products_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coupon_products
    ADD CONSTRAINT coupon_products_pkey PRIMARY KEY (coupon_id, product_id);


--
-- Name: coupon_segments coupon_segments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coupon_segments
    ADD CONSTRAINT coupon_segments_pkey PRIMARY KEY (coupon_id, segment);


--
-- Name: coupon_usages coupon_usages_coupon_id_order_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coupon_usages
    ADD CONSTRAINT coupon_usages_coupon_id_order_id_key UNIQUE (coupon_id, order_id);


--
-- Name: coupon_usages coupon_usages_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coupon_usages
    ADD CONSTRAINT coupon_usages_pkey PRIMARY KEY (id);


--
-- Name: coupons coupons_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coupons
    ADD CONSTRAINT coupons_code_key UNIQUE (code);


--
-- Name: coupons coupons_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coupons
    ADD CONSTRAINT coupons_pkey PRIMARY KEY (id);


--
-- Name: favorites favorites_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.favorites
    ADD CONSTRAINT favorites_pkey PRIMARY KEY (id);


--
-- Name: flash_sale_items flash_sale_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.flash_sale_items
    ADD CONSTRAINT flash_sale_items_pkey PRIMARY KEY (id);


--
-- Name: flash_sales flash_sales_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.flash_sales
    ADD CONSTRAINT flash_sales_pkey PRIMARY KEY (id);


--
-- Name: inventory_logs inventory_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inventory_logs
    ADD CONSTRAINT inventory_logs_pkey PRIMARY KEY (id);


--
-- Name: order_items order_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_items
    ADD CONSTRAINT order_items_pkey PRIMARY KEY (id);


--
-- Name: orders orders_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_pkey PRIMARY KEY (id);


--
-- Name: payments payments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_pkey PRIMARY KEY (id);


--
-- Name: permission_groups permission_groups_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.permission_groups
    ADD CONSTRAINT permission_groups_pkey PRIMARY KEY (id);


--
-- Name: permissions permissions_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.permissions
    ADD CONSTRAINT permissions_code_key UNIQUE (code);


--
-- Name: permissions permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.permissions
    ADD CONSTRAINT permissions_pkey PRIMARY KEY (id);


--
-- Name: product_analytics product_analytics_master_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_analytics
    ADD CONSTRAINT product_analytics_master_key UNIQUE (product_id, channel, source, report_date);


--
-- Name: product_analytics product_analytics_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_analytics
    ADD CONSTRAINT product_analytics_pkey PRIMARY KEY (id);


--
-- Name: product_images product_images_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_images
    ADD CONSTRAINT product_images_pkey PRIMARY KEY (id);


--
-- Name: product_reviews product_reviews_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_reviews
    ADD CONSTRAINT product_reviews_pkey PRIMARY KEY (id);


--
-- Name: product_variants product_variants_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_variants
    ADD CONSTRAINT product_variants_pkey PRIMARY KEY (id);


--
-- Name: product_variants product_variants_sku_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_variants
    ADD CONSTRAINT product_variants_sku_key UNIQUE (sku);


--
-- Name: products products_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_pkey PRIMARY KEY (id);


--
-- Name: return_requests return_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.return_requests
    ADD CONSTRAINT return_requests_pkey PRIMARY KEY (id);


--
-- Name: role_permissions role_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_permissions
    ADD CONSTRAINT role_permissions_pkey PRIMARY KEY (role_id, permission_id);


--
-- Name: roles roles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_pkey PRIMARY KEY (id);


--
-- Name: shipment_events shipment_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shipment_events
    ADD CONSTRAINT shipment_events_pkey PRIMARY KEY (id);


--
-- Name: shipments shipments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shipments
    ADD CONSTRAINT shipments_pkey PRIMARY KEY (id);


--
-- Name: shipping_configs shipping_configs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shipping_configs
    ADD CONSTRAINT shipping_configs_pkey PRIMARY KEY (id);


--
-- Name: shipping_providers shipping_providers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shipping_providers
    ADD CONSTRAINT shipping_providers_pkey PRIMARY KEY (id);


--
-- Name: system_settings system_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.system_settings
    ADD CONSTRAINT system_settings_pkey PRIMARY KEY (id);


--
-- Name: tenants tenants_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenants
    ADD CONSTRAINT tenants_pkey PRIMARY KEY (id);


--
-- Name: cart_items unique_cart_item; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cart_items
    ADD CONSTRAINT unique_cart_item UNIQUE (user_id, product_id, size);


--
-- Name: favorites unique_user_product; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.favorites
    ADD CONSTRAINT unique_user_product UNIQUE (user_id, product_id);


--
-- Name: user_addresses user_addresses_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_addresses
    ADD CONSTRAINT user_addresses_pkey PRIMARY KEY (id);


--
-- Name: user_permissions user_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_permissions
    ADD CONSTRAINT user_permissions_pkey PRIMARY KEY (user_id, permission_id);


--
-- Name: user_roles user_roles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_roles
    ADD CONSTRAINT user_roles_pkey PRIMARY KEY (user_id, role_id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: product_variants variant_unique_combination; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_variants
    ADD CONSTRAINT variant_unique_combination UNIQUE (product_id, size, color_name);


--
-- Name: messages messages_pkey; Type: CONSTRAINT; Schema: realtime; Owner: -
--

ALTER TABLE ONLY realtime.messages
    ADD CONSTRAINT messages_pkey PRIMARY KEY (id, inserted_at);


--
-- Name: subscription pk_subscription; Type: CONSTRAINT; Schema: realtime; Owner: -
--

ALTER TABLE ONLY realtime.subscription
    ADD CONSTRAINT pk_subscription PRIMARY KEY (id);


--
-- Name: schema_migrations schema_migrations_pkey; Type: CONSTRAINT; Schema: realtime; Owner: -
--

ALTER TABLE ONLY realtime.schema_migrations
    ADD CONSTRAINT schema_migrations_pkey PRIMARY KEY (version);


--
-- Name: buckets_analytics buckets_analytics_pkey; Type: CONSTRAINT; Schema: storage; Owner: -
--

ALTER TABLE ONLY storage.buckets_analytics
    ADD CONSTRAINT buckets_analytics_pkey PRIMARY KEY (id);


--
-- Name: buckets buckets_pkey; Type: CONSTRAINT; Schema: storage; Owner: -
--

ALTER TABLE ONLY storage.buckets
    ADD CONSTRAINT buckets_pkey PRIMARY KEY (id);


--
-- Name: buckets_vectors buckets_vectors_pkey; Type: CONSTRAINT; Schema: storage; Owner: -
--

ALTER TABLE ONLY storage.buckets_vectors
    ADD CONSTRAINT buckets_vectors_pkey PRIMARY KEY (id);


--
-- Name: migrations migrations_name_key; Type: CONSTRAINT; Schema: storage; Owner: -
--

ALTER TABLE ONLY storage.migrations
    ADD CONSTRAINT migrations_name_key UNIQUE (name);


--
-- Name: migrations migrations_pkey; Type: CONSTRAINT; Schema: storage; Owner: -
--

ALTER TABLE ONLY storage.migrations
    ADD CONSTRAINT migrations_pkey PRIMARY KEY (id);


--
-- Name: objects objects_pkey; Type: CONSTRAINT; Schema: storage; Owner: -
--

ALTER TABLE ONLY storage.objects
    ADD CONSTRAINT objects_pkey PRIMARY KEY (id);


--
-- Name: s3_multipart_uploads_parts s3_multipart_uploads_parts_pkey; Type: CONSTRAINT; Schema: storage; Owner: -
--

ALTER TABLE ONLY storage.s3_multipart_uploads_parts
    ADD CONSTRAINT s3_multipart_uploads_parts_pkey PRIMARY KEY (id);


--
-- Name: s3_multipart_uploads s3_multipart_uploads_pkey; Type: CONSTRAINT; Schema: storage; Owner: -
--

ALTER TABLE ONLY storage.s3_multipart_uploads
    ADD CONSTRAINT s3_multipart_uploads_pkey PRIMARY KEY (id);


--
-- Name: vector_indexes vector_indexes_pkey; Type: CONSTRAINT; Schema: storage; Owner: -
--

ALTER TABLE ONLY storage.vector_indexes
    ADD CONSTRAINT vector_indexes_pkey PRIMARY KEY (id);


--
-- Name: audit_logs_instance_id_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX audit_logs_instance_id_idx ON auth.audit_log_entries USING btree (instance_id);


--
-- Name: confirmation_token_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE UNIQUE INDEX confirmation_token_idx ON auth.users USING btree (confirmation_token) WHERE ((confirmation_token)::text !~ '^[0-9 ]*$'::text);


--
-- Name: custom_oauth_providers_created_at_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX custom_oauth_providers_created_at_idx ON auth.custom_oauth_providers USING btree (created_at);


--
-- Name: custom_oauth_providers_enabled_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX custom_oauth_providers_enabled_idx ON auth.custom_oauth_providers USING btree (enabled);


--
-- Name: custom_oauth_providers_identifier_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX custom_oauth_providers_identifier_idx ON auth.custom_oauth_providers USING btree (identifier);


--
-- Name: custom_oauth_providers_provider_type_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX custom_oauth_providers_provider_type_idx ON auth.custom_oauth_providers USING btree (provider_type);


--
-- Name: email_change_token_current_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE UNIQUE INDEX email_change_token_current_idx ON auth.users USING btree (email_change_token_current) WHERE ((email_change_token_current)::text !~ '^[0-9 ]*$'::text);


--
-- Name: email_change_token_new_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE UNIQUE INDEX email_change_token_new_idx ON auth.users USING btree (email_change_token_new) WHERE ((email_change_token_new)::text !~ '^[0-9 ]*$'::text);


--
-- Name: factor_id_created_at_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX factor_id_created_at_idx ON auth.mfa_factors USING btree (user_id, created_at);


--
-- Name: flow_state_created_at_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX flow_state_created_at_idx ON auth.flow_state USING btree (created_at DESC);


--
-- Name: identities_email_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX identities_email_idx ON auth.identities USING btree (email text_pattern_ops);


--
-- Name: INDEX identities_email_idx; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON INDEX auth.identities_email_idx IS 'Auth: Ensures indexed queries on the email column';


--
-- Name: identities_user_id_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX identities_user_id_idx ON auth.identities USING btree (user_id);


--
-- Name: idx_auth_code; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX idx_auth_code ON auth.flow_state USING btree (auth_code);


--
-- Name: idx_oauth_client_states_created_at; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX idx_oauth_client_states_created_at ON auth.oauth_client_states USING btree (created_at);


--
-- Name: idx_user_id_auth_method; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX idx_user_id_auth_method ON auth.flow_state USING btree (user_id, authentication_method);


--
-- Name: idx_users_created_at_desc; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX idx_users_created_at_desc ON auth.users USING btree (created_at DESC);


--
-- Name: idx_users_email; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX idx_users_email ON auth.users USING btree (email);


--
-- Name: idx_users_last_sign_in_at_desc; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX idx_users_last_sign_in_at_desc ON auth.users USING btree (last_sign_in_at DESC);


--
-- Name: idx_users_name; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX idx_users_name ON auth.users USING btree (((raw_user_meta_data ->> 'name'::text))) WHERE ((raw_user_meta_data ->> 'name'::text) IS NOT NULL);


--
-- Name: mfa_challenge_created_at_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX mfa_challenge_created_at_idx ON auth.mfa_challenges USING btree (created_at DESC);


--
-- Name: mfa_factors_user_friendly_name_unique; Type: INDEX; Schema: auth; Owner: -
--

CREATE UNIQUE INDEX mfa_factors_user_friendly_name_unique ON auth.mfa_factors USING btree (friendly_name, user_id) WHERE (TRIM(BOTH FROM friendly_name) <> ''::text);


--
-- Name: mfa_factors_user_id_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX mfa_factors_user_id_idx ON auth.mfa_factors USING btree (user_id);


--
-- Name: oauth_auth_pending_exp_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX oauth_auth_pending_exp_idx ON auth.oauth_authorizations USING btree (expires_at) WHERE (status = 'pending'::auth.oauth_authorization_status);


--
-- Name: oauth_clients_deleted_at_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX oauth_clients_deleted_at_idx ON auth.oauth_clients USING btree (deleted_at);


--
-- Name: oauth_consents_active_client_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX oauth_consents_active_client_idx ON auth.oauth_consents USING btree (client_id) WHERE (revoked_at IS NULL);


--
-- Name: oauth_consents_active_user_client_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX oauth_consents_active_user_client_idx ON auth.oauth_consents USING btree (user_id, client_id) WHERE (revoked_at IS NULL);


--
-- Name: oauth_consents_user_order_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX oauth_consents_user_order_idx ON auth.oauth_consents USING btree (user_id, granted_at DESC);


--
-- Name: one_time_tokens_relates_to_hash_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX one_time_tokens_relates_to_hash_idx ON auth.one_time_tokens USING hash (relates_to);


--
-- Name: one_time_tokens_token_hash_hash_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX one_time_tokens_token_hash_hash_idx ON auth.one_time_tokens USING hash (token_hash);


--
-- Name: one_time_tokens_user_id_token_type_key; Type: INDEX; Schema: auth; Owner: -
--

CREATE UNIQUE INDEX one_time_tokens_user_id_token_type_key ON auth.one_time_tokens USING btree (user_id, token_type);


--
-- Name: reauthentication_token_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE UNIQUE INDEX reauthentication_token_idx ON auth.users USING btree (reauthentication_token) WHERE ((reauthentication_token)::text !~ '^[0-9 ]*$'::text);


--
-- Name: recovery_token_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE UNIQUE INDEX recovery_token_idx ON auth.users USING btree (recovery_token) WHERE ((recovery_token)::text !~ '^[0-9 ]*$'::text);


--
-- Name: refresh_tokens_instance_id_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX refresh_tokens_instance_id_idx ON auth.refresh_tokens USING btree (instance_id);


--
-- Name: refresh_tokens_instance_id_user_id_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX refresh_tokens_instance_id_user_id_idx ON auth.refresh_tokens USING btree (instance_id, user_id);


--
-- Name: refresh_tokens_parent_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX refresh_tokens_parent_idx ON auth.refresh_tokens USING btree (parent);


--
-- Name: refresh_tokens_session_id_revoked_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX refresh_tokens_session_id_revoked_idx ON auth.refresh_tokens USING btree (session_id, revoked);


--
-- Name: refresh_tokens_updated_at_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX refresh_tokens_updated_at_idx ON auth.refresh_tokens USING btree (updated_at DESC);


--
-- Name: saml_providers_sso_provider_id_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX saml_providers_sso_provider_id_idx ON auth.saml_providers USING btree (sso_provider_id);


--
-- Name: saml_relay_states_created_at_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX saml_relay_states_created_at_idx ON auth.saml_relay_states USING btree (created_at DESC);


--
-- Name: saml_relay_states_for_email_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX saml_relay_states_for_email_idx ON auth.saml_relay_states USING btree (for_email);


--
-- Name: saml_relay_states_sso_provider_id_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX saml_relay_states_sso_provider_id_idx ON auth.saml_relay_states USING btree (sso_provider_id);


--
-- Name: sessions_not_after_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX sessions_not_after_idx ON auth.sessions USING btree (not_after DESC);


--
-- Name: sessions_oauth_client_id_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX sessions_oauth_client_id_idx ON auth.sessions USING btree (oauth_client_id);


--
-- Name: sessions_user_id_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX sessions_user_id_idx ON auth.sessions USING btree (user_id);


--
-- Name: sso_domains_domain_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE UNIQUE INDEX sso_domains_domain_idx ON auth.sso_domains USING btree (lower(domain));


--
-- Name: sso_domains_sso_provider_id_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX sso_domains_sso_provider_id_idx ON auth.sso_domains USING btree (sso_provider_id);


--
-- Name: sso_providers_resource_id_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE UNIQUE INDEX sso_providers_resource_id_idx ON auth.sso_providers USING btree (lower(resource_id));


--
-- Name: sso_providers_resource_id_pattern_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX sso_providers_resource_id_pattern_idx ON auth.sso_providers USING btree (resource_id text_pattern_ops);


--
-- Name: unique_phone_factor_per_user; Type: INDEX; Schema: auth; Owner: -
--

CREATE UNIQUE INDEX unique_phone_factor_per_user ON auth.mfa_factors USING btree (user_id, phone);


--
-- Name: user_id_created_at_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX user_id_created_at_idx ON auth.sessions USING btree (user_id, created_at);


--
-- Name: users_email_partial_key; Type: INDEX; Schema: auth; Owner: -
--

CREATE UNIQUE INDEX users_email_partial_key ON auth.users USING btree (email) WHERE (is_sso_user = false);


--
-- Name: INDEX users_email_partial_key; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON INDEX auth.users_email_partial_key IS 'Auth: A partial unique index that applies only when is_sso_user is false';


--
-- Name: users_instance_id_email_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX users_instance_id_email_idx ON auth.users USING btree (instance_id, lower((email)::text));


--
-- Name: users_instance_id_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX users_instance_id_idx ON auth.users USING btree (instance_id);


--
-- Name: users_is_anonymous_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX users_is_anonymous_idx ON auth.users USING btree (is_anonymous);


--
-- Name: webauthn_challenges_expires_at_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX webauthn_challenges_expires_at_idx ON auth.webauthn_challenges USING btree (expires_at);


--
-- Name: webauthn_challenges_user_id_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX webauthn_challenges_user_id_idx ON auth.webauthn_challenges USING btree (user_id);


--
-- Name: webauthn_credentials_credential_id_key; Type: INDEX; Schema: auth; Owner: -
--

CREATE UNIQUE INDEX webauthn_credentials_credential_id_key ON auth.webauthn_credentials USING btree (credential_id);


--
-- Name: webauthn_credentials_user_id_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX webauthn_credentials_user_id_idx ON auth.webauthn_credentials USING btree (user_id);


--
-- Name: idx_audit_logs_new_values; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_logs_new_values ON public.audit_logs USING gin (new_values);


--
-- Name: idx_audit_logs_old_values; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_logs_old_values ON public.audit_logs USING gin (old_values);


--
-- Name: idx_audit_logs_table_record; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_logs_table_record ON public.audit_logs USING btree (table_name, record_id);


--
-- Name: idx_audit_logs_user_action; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_logs_user_action ON public.audit_logs USING btree (user_id, action);


--
-- Name: idx_cart_items_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_cart_items_user_id ON public.cart_items USING btree (user_id);


--
-- Name: idx_cart_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_cart_user ON public.cart_items USING btree (user_id);


--
-- Name: idx_coupon_categories; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_coupon_categories ON public.coupon_categories USING btree (category_id);


--
-- Name: idx_coupon_products; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_coupon_products ON public.coupon_products USING btree (product_id);


--
-- Name: idx_coupon_usages_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_coupon_usages_user ON public.coupon_usages USING btree (coupon_id, user_id);


--
-- Name: idx_coupons_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_coupons_active ON public.coupons USING btree (is_active, starts_at, expires_at);


--
-- Name: idx_favorites_product; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_favorites_product ON public.favorites USING btree (product_id);


--
-- Name: idx_favorites_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_favorites_user ON public.favorites USING btree (user_id);


--
-- Name: idx_favorites_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_favorites_user_id ON public.favorites USING btree (user_id);


--
-- Name: idx_order_items_order; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_order_items_order ON public.order_items USING btree (order_id);


--
-- Name: idx_order_items_order_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_order_items_order_id ON public.order_items USING btree (order_id);


--
-- Name: idx_orders_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_orders_created_at ON public.orders USING btree (created_at DESC);


--
-- Name: idx_orders_shipping_address; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_orders_shipping_address ON public.orders USING gin (shipping_address);


--
-- Name: idx_orders_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_orders_status ON public.orders USING btree (status);


--
-- Name: idx_orders_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_orders_user ON public.orders USING btree (user_id);


--
-- Name: idx_orders_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_orders_user_id ON public.orders USING btree (user_id);


--
-- Name: idx_pa_channel; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pa_channel ON public.product_analytics USING btree (channel);


--
-- Name: idx_pa_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pa_date ON public.product_analytics USING btree (report_date);


--
-- Name: idx_pa_product; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pa_product ON public.product_analytics USING btree (product_id);


--
-- Name: idx_product_images_product; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_product_images_product ON public.product_images USING btree (product_id);


--
-- Name: idx_products_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_products_category ON public.products USING btree (category_id);


--
-- Name: idx_products_category_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_products_category_id ON public.products USING btree (category_id);


--
-- Name: idx_products_featured; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_products_featured ON public.products USING btree (is_featured) WHERE (is_featured = true);


--
-- Name: idx_products_is_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_products_is_active ON public.products USING btree (is_active) WHERE (is_active = true);


--
-- Name: idx_products_slug; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_products_slug ON public.products USING btree (slug);


--
-- Name: idx_return_requests_order; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_return_requests_order ON public.return_requests USING btree (order_id);


--
-- Name: idx_return_requests_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_return_requests_status ON public.return_requests USING btree (status);


--
-- Name: idx_return_requests_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_return_requests_user ON public.return_requests USING btree (user_id);


--
-- Name: idx_shipments_raw_response; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_shipments_raw_response ON public.shipments USING gin (raw_response);


--
-- Name: idx_shipments_status_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_shipments_status_created ON public.shipments USING btree (status, created_at DESC);


--
-- Name: idx_shipments_tracking_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_shipments_tracking_code ON public.shipments USING btree (tracking_code);


--
-- Name: idx_user_addresses_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_user_addresses_user_id ON public.user_addresses USING btree (user_id);


--
-- Name: idx_variants_product; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_variants_product ON public.product_variants USING btree (product_id);


--
-- Name: idx_webhook_logs_provider_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_webhook_logs_provider_created ON public.webhook_logs USING btree (provider, created_at DESC);


--
-- Name: textsearch_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX textsearch_idx ON public.products USING gin (textsearchable_index_col);


--
-- Name: ix_realtime_subscription_entity; Type: INDEX; Schema: realtime; Owner: -
--

CREATE INDEX ix_realtime_subscription_entity ON realtime.subscription USING btree (entity);


--
-- Name: messages_inserted_at_topic_index; Type: INDEX; Schema: realtime; Owner: -
--

CREATE INDEX messages_inserted_at_topic_index ON ONLY realtime.messages USING btree (inserted_at DESC, topic) WHERE ((extension = 'broadcast'::text) AND (private IS TRUE));


--
-- Name: subscription_subscription_id_entity_filters_action_filter_key; Type: INDEX; Schema: realtime; Owner: -
--

CREATE UNIQUE INDEX subscription_subscription_id_entity_filters_action_filter_key ON realtime.subscription USING btree (subscription_id, entity, filters, action_filter);


--
-- Name: bname; Type: INDEX; Schema: storage; Owner: -
--

CREATE UNIQUE INDEX bname ON storage.buckets USING btree (name);


--
-- Name: bucketid_objname; Type: INDEX; Schema: storage; Owner: -
--

CREATE UNIQUE INDEX bucketid_objname ON storage.objects USING btree (bucket_id, name);


--
-- Name: buckets_analytics_unique_name_idx; Type: INDEX; Schema: storage; Owner: -
--

CREATE UNIQUE INDEX buckets_analytics_unique_name_idx ON storage.buckets_analytics USING btree (name) WHERE (deleted_at IS NULL);


--
-- Name: idx_multipart_uploads_list; Type: INDEX; Schema: storage; Owner: -
--

CREATE INDEX idx_multipart_uploads_list ON storage.s3_multipart_uploads USING btree (bucket_id, key, created_at);


--
-- Name: idx_objects_bucket_id_name; Type: INDEX; Schema: storage; Owner: -
--

CREATE INDEX idx_objects_bucket_id_name ON storage.objects USING btree (bucket_id, name COLLATE "C");


--
-- Name: idx_objects_bucket_id_name_lower; Type: INDEX; Schema: storage; Owner: -
--

CREATE INDEX idx_objects_bucket_id_name_lower ON storage.objects USING btree (bucket_id, lower(name) COLLATE "C");


--
-- Name: name_prefix_search; Type: INDEX; Schema: storage; Owner: -
--

CREATE INDEX name_prefix_search ON storage.objects USING btree (name text_pattern_ops);


--
-- Name: vector_indexes_name_bucket_id_idx; Type: INDEX; Schema: storage; Owner: -
--

CREATE UNIQUE INDEX vector_indexes_name_bucket_id_idx ON storage.vector_indexes USING btree (name, bucket_id);


--
-- Name: categories update_categories_modtime; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_categories_modtime BEFORE UPDATE ON public.categories FOR EACH ROW EXECUTE FUNCTION public.update_modified_column();


--
-- Name: shipments update_shipments_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_shipments_updated_at BEFORE UPDATE ON public.shipments FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: subscription tr_check_filters; Type: TRIGGER; Schema: realtime; Owner: -
--

CREATE TRIGGER tr_check_filters BEFORE INSERT OR UPDATE ON realtime.subscription FOR EACH ROW EXECUTE FUNCTION realtime.subscription_check_filters();


--
-- Name: buckets enforce_bucket_name_length_trigger; Type: TRIGGER; Schema: storage; Owner: -
--

CREATE TRIGGER enforce_bucket_name_length_trigger BEFORE INSERT OR UPDATE OF name ON storage.buckets FOR EACH ROW EXECUTE FUNCTION storage.enforce_bucket_name_length();


--
-- Name: buckets protect_buckets_delete; Type: TRIGGER; Schema: storage; Owner: -
--

CREATE TRIGGER protect_buckets_delete BEFORE DELETE ON storage.buckets FOR EACH STATEMENT EXECUTE FUNCTION storage.protect_delete();


--
-- Name: objects protect_objects_delete; Type: TRIGGER; Schema: storage; Owner: -
--

CREATE TRIGGER protect_objects_delete BEFORE DELETE ON storage.objects FOR EACH STATEMENT EXECUTE FUNCTION storage.protect_delete();


--
-- Name: objects update_objects_updated_at; Type: TRIGGER; Schema: storage; Owner: -
--

CREATE TRIGGER update_objects_updated_at BEFORE UPDATE ON storage.objects FOR EACH ROW EXECUTE FUNCTION storage.update_updated_at_column();


--
-- Name: identities identities_user_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.identities
    ADD CONSTRAINT identities_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;


--
-- Name: mfa_amr_claims mfa_amr_claims_session_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.mfa_amr_claims
    ADD CONSTRAINT mfa_amr_claims_session_id_fkey FOREIGN KEY (session_id) REFERENCES auth.sessions(id) ON DELETE CASCADE;


--
-- Name: mfa_challenges mfa_challenges_auth_factor_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.mfa_challenges
    ADD CONSTRAINT mfa_challenges_auth_factor_id_fkey FOREIGN KEY (factor_id) REFERENCES auth.mfa_factors(id) ON DELETE CASCADE;


--
-- Name: mfa_factors mfa_factors_user_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.mfa_factors
    ADD CONSTRAINT mfa_factors_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;


--
-- Name: oauth_authorizations oauth_authorizations_client_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.oauth_authorizations
    ADD CONSTRAINT oauth_authorizations_client_id_fkey FOREIGN KEY (client_id) REFERENCES auth.oauth_clients(id) ON DELETE CASCADE;


--
-- Name: oauth_authorizations oauth_authorizations_user_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.oauth_authorizations
    ADD CONSTRAINT oauth_authorizations_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;


--
-- Name: oauth_consents oauth_consents_client_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.oauth_consents
    ADD CONSTRAINT oauth_consents_client_id_fkey FOREIGN KEY (client_id) REFERENCES auth.oauth_clients(id) ON DELETE CASCADE;


--
-- Name: oauth_consents oauth_consents_user_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.oauth_consents
    ADD CONSTRAINT oauth_consents_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;


--
-- Name: one_time_tokens one_time_tokens_user_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.one_time_tokens
    ADD CONSTRAINT one_time_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;


--
-- Name: refresh_tokens refresh_tokens_session_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.refresh_tokens
    ADD CONSTRAINT refresh_tokens_session_id_fkey FOREIGN KEY (session_id) REFERENCES auth.sessions(id) ON DELETE CASCADE;


--
-- Name: saml_providers saml_providers_sso_provider_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.saml_providers
    ADD CONSTRAINT saml_providers_sso_provider_id_fkey FOREIGN KEY (sso_provider_id) REFERENCES auth.sso_providers(id) ON DELETE CASCADE;


--
-- Name: saml_relay_states saml_relay_states_flow_state_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.saml_relay_states
    ADD CONSTRAINT saml_relay_states_flow_state_id_fkey FOREIGN KEY (flow_state_id) REFERENCES auth.flow_state(id) ON DELETE CASCADE;


--
-- Name: saml_relay_states saml_relay_states_sso_provider_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.saml_relay_states
    ADD CONSTRAINT saml_relay_states_sso_provider_id_fkey FOREIGN KEY (sso_provider_id) REFERENCES auth.sso_providers(id) ON DELETE CASCADE;


--
-- Name: sessions sessions_oauth_client_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.sessions
    ADD CONSTRAINT sessions_oauth_client_id_fkey FOREIGN KEY (oauth_client_id) REFERENCES auth.oauth_clients(id) ON DELETE CASCADE;


--
-- Name: sessions sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.sessions
    ADD CONSTRAINT sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;


--
-- Name: sso_domains sso_domains_sso_provider_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.sso_domains
    ADD CONSTRAINT sso_domains_sso_provider_id_fkey FOREIGN KEY (sso_provider_id) REFERENCES auth.sso_providers(id) ON DELETE CASCADE;


--
-- Name: webauthn_challenges webauthn_challenges_user_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.webauthn_challenges
    ADD CONSTRAINT webauthn_challenges_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;


--
-- Name: webauthn_credentials webauthn_credentials_user_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.webauthn_credentials
    ADD CONSTRAINT webauthn_credentials_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;


--
-- Name: audit_logs audit_logs_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: audit_logs audit_logs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: cart_items cart_items_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cart_items
    ADD CONSTRAINT cart_items_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id) ON DELETE CASCADE;


--
-- Name: cart_items cart_items_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cart_items
    ADD CONSTRAINT cart_items_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: cart_items cart_items_variant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cart_items
    ADD CONSTRAINT cart_items_variant_id_fkey FOREIGN KEY (variant_id) REFERENCES public.product_variants(id) ON DELETE CASCADE;


--
-- Name: categories categories_parent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.categories
    ADD CONSTRAINT categories_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES public.categories(id) ON DELETE SET NULL;


--
-- Name: coupon_categories coupon_categories_coupon_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coupon_categories
    ADD CONSTRAINT coupon_categories_coupon_id_fkey FOREIGN KEY (coupon_id) REFERENCES public.coupons(id) ON DELETE CASCADE;


--
-- Name: coupon_products coupon_products_coupon_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coupon_products
    ADD CONSTRAINT coupon_products_coupon_id_fkey FOREIGN KEY (coupon_id) REFERENCES public.coupons(id) ON DELETE CASCADE;


--
-- Name: coupon_segments coupon_segments_coupon_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coupon_segments
    ADD CONSTRAINT coupon_segments_coupon_id_fkey FOREIGN KEY (coupon_id) REFERENCES public.coupons(id) ON DELETE CASCADE;


--
-- Name: coupon_usages coupon_usages_coupon_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coupon_usages
    ADD CONSTRAINT coupon_usages_coupon_id_fkey FOREIGN KEY (coupon_id) REFERENCES public.coupons(id) ON DELETE CASCADE;


--
-- Name: coupon_usages coupon_usages_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coupon_usages
    ADD CONSTRAINT coupon_usages_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE CASCADE;


--
-- Name: favorites favorites_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.favorites
    ADD CONSTRAINT favorites_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id) ON DELETE CASCADE;


--
-- Name: order_items fk_order_items_variants; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_items
    ADD CONSTRAINT fk_order_items_variants FOREIGN KEY (variant_id) REFERENCES public.product_variants(id) ON DELETE SET NULL;


--
-- Name: flash_sale_items flash_sale_items_flash_sale_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.flash_sale_items
    ADD CONSTRAINT flash_sale_items_flash_sale_id_fkey FOREIGN KEY (flash_sale_id) REFERENCES public.flash_sales(id) ON DELETE CASCADE;


--
-- Name: flash_sale_items flash_sale_items_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.flash_sale_items
    ADD CONSTRAINT flash_sale_items_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id) ON DELETE CASCADE;


--
-- Name: flash_sale_items flash_sale_items_variant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.flash_sale_items
    ADD CONSTRAINT flash_sale_items_variant_id_fkey FOREIGN KEY (variant_id) REFERENCES public.product_variants(id) ON DELETE CASCADE;


--
-- Name: inventory_logs inventory_logs_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inventory_logs
    ADD CONSTRAINT inventory_logs_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: inventory_logs inventory_logs_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inventory_logs
    ADD CONSTRAINT inventory_logs_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id) ON DELETE CASCADE;


--
-- Name: inventory_logs inventory_logs_variant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inventory_logs
    ADD CONSTRAINT inventory_logs_variant_id_fkey FOREIGN KEY (variant_id) REFERENCES public.product_variants(id) ON DELETE CASCADE;


--
-- Name: order_items order_items_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_items
    ADD CONSTRAINT order_items_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE CASCADE;


--
-- Name: order_items order_items_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_items
    ADD CONSTRAINT order_items_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id) ON DELETE SET NULL;


--
-- Name: orders orders_coupon_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_coupon_id_fkey FOREIGN KEY (coupon_id) REFERENCES public.coupons(id);


--
-- Name: orders orders_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: payments payments_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE CASCADE;


--
-- Name: permissions permissions_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.permissions
    ADD CONSTRAINT permissions_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.permission_groups(id);


--
-- Name: product_analytics product_analytics_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_analytics
    ADD CONSTRAINT product_analytics_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id);


--
-- Name: product_images product_images_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_images
    ADD CONSTRAINT product_images_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id) ON DELETE CASCADE;


--
-- Name: product_reviews product_reviews_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_reviews
    ADD CONSTRAINT product_reviews_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE SET NULL;


--
-- Name: product_reviews product_reviews_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_reviews
    ADD CONSTRAINT product_reviews_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id) ON DELETE CASCADE;


--
-- Name: product_reviews product_reviews_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_reviews
    ADD CONSTRAINT product_reviews_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: product_variants product_variants_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_variants
    ADD CONSTRAINT product_variants_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id) ON DELETE CASCADE;


--
-- Name: products products_brand_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_brand_id_fkey FOREIGN KEY (brand_id) REFERENCES public.brands(id) ON DELETE SET NULL;


--
-- Name: products products_category_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_category_id_fkey FOREIGN KEY (category_id) REFERENCES public.categories(id) ON DELETE SET NULL;


--
-- Name: return_requests return_requests_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.return_requests
    ADD CONSTRAINT return_requests_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE CASCADE;


--
-- Name: return_requests return_requests_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.return_requests
    ADD CONSTRAINT return_requests_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: role_permissions role_permissions_permission_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_permissions
    ADD CONSTRAINT role_permissions_permission_id_fkey FOREIGN KEY (permission_id) REFERENCES public.permissions(id) ON DELETE CASCADE;


--
-- Name: role_permissions role_permissions_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_permissions
    ADD CONSTRAINT role_permissions_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id) ON DELETE CASCADE;


--
-- Name: roles roles_parent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES public.roles(id);


--
-- Name: roles roles_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: shipment_events shipment_events_shipment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shipment_events
    ADD CONSTRAINT shipment_events_shipment_id_fkey FOREIGN KEY (shipment_id) REFERENCES public.shipments(id) ON DELETE CASCADE;


--
-- Name: shipments shipments_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shipments
    ADD CONSTRAINT shipments_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE CASCADE;


--
-- Name: user_addresses user_addresses_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_addresses
    ADD CONSTRAINT user_addresses_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: user_permissions user_permissions_permission_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_permissions
    ADD CONSTRAINT user_permissions_permission_id_fkey FOREIGN KEY (permission_id) REFERENCES public.permissions(id) ON DELETE CASCADE;


--
-- Name: user_permissions user_permissions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_permissions
    ADD CONSTRAINT user_permissions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: user_roles user_roles_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_roles
    ADD CONSTRAINT user_roles_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id) ON DELETE CASCADE;


--
-- Name: user_roles user_roles_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_roles
    ADD CONSTRAINT user_roles_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: user_roles user_roles_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_roles
    ADD CONSTRAINT user_roles_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: objects objects_bucketId_fkey; Type: FK CONSTRAINT; Schema: storage; Owner: -
--

ALTER TABLE ONLY storage.objects
    ADD CONSTRAINT "objects_bucketId_fkey" FOREIGN KEY (bucket_id) REFERENCES storage.buckets(id);


--
-- Name: s3_multipart_uploads s3_multipart_uploads_bucket_id_fkey; Type: FK CONSTRAINT; Schema: storage; Owner: -
--

ALTER TABLE ONLY storage.s3_multipart_uploads
    ADD CONSTRAINT s3_multipart_uploads_bucket_id_fkey FOREIGN KEY (bucket_id) REFERENCES storage.buckets(id);


--
-- Name: s3_multipart_uploads_parts s3_multipart_uploads_parts_bucket_id_fkey; Type: FK CONSTRAINT; Schema: storage; Owner: -
--

ALTER TABLE ONLY storage.s3_multipart_uploads_parts
    ADD CONSTRAINT s3_multipart_uploads_parts_bucket_id_fkey FOREIGN KEY (bucket_id) REFERENCES storage.buckets(id);


--
-- Name: s3_multipart_uploads_parts s3_multipart_uploads_parts_upload_id_fkey; Type: FK CONSTRAINT; Schema: storage; Owner: -
--

ALTER TABLE ONLY storage.s3_multipart_uploads_parts
    ADD CONSTRAINT s3_multipart_uploads_parts_upload_id_fkey FOREIGN KEY (upload_id) REFERENCES storage.s3_multipart_uploads(id) ON DELETE CASCADE;


--
-- Name: vector_indexes vector_indexes_bucket_id_fkey; Type: FK CONSTRAINT; Schema: storage; Owner: -
--

ALTER TABLE ONLY storage.vector_indexes
    ADD CONSTRAINT vector_indexes_bucket_id_fkey FOREIGN KEY (bucket_id) REFERENCES storage.buckets_vectors(id);


--
-- Name: audit_log_entries; Type: ROW SECURITY; Schema: auth; Owner: -
--

ALTER TABLE auth.audit_log_entries ENABLE ROW LEVEL SECURITY;

--
-- Name: flow_state; Type: ROW SECURITY; Schema: auth; Owner: -
--

ALTER TABLE auth.flow_state ENABLE ROW LEVEL SECURITY;

--
-- Name: identities; Type: ROW SECURITY; Schema: auth; Owner: -
--

ALTER TABLE auth.identities ENABLE ROW LEVEL SECURITY;

--
-- Name: instances; Type: ROW SECURITY; Schema: auth; Owner: -
--

ALTER TABLE auth.instances ENABLE ROW LEVEL SECURITY;

--
-- Name: mfa_amr_claims; Type: ROW SECURITY; Schema: auth; Owner: -
--

ALTER TABLE auth.mfa_amr_claims ENABLE ROW LEVEL SECURITY;

--
-- Name: mfa_challenges; Type: ROW SECURITY; Schema: auth; Owner: -
--

ALTER TABLE auth.mfa_challenges ENABLE ROW LEVEL SECURITY;

--
-- Name: mfa_factors; Type: ROW SECURITY; Schema: auth; Owner: -
--

ALTER TABLE auth.mfa_factors ENABLE ROW LEVEL SECURITY;

--
-- Name: one_time_tokens; Type: ROW SECURITY; Schema: auth; Owner: -
--

ALTER TABLE auth.one_time_tokens ENABLE ROW LEVEL SECURITY;

--
-- Name: refresh_tokens; Type: ROW SECURITY; Schema: auth; Owner: -
--

ALTER TABLE auth.refresh_tokens ENABLE ROW LEVEL SECURITY;

--
-- Name: saml_providers; Type: ROW SECURITY; Schema: auth; Owner: -
--

ALTER TABLE auth.saml_providers ENABLE ROW LEVEL SECURITY;

--
-- Name: saml_relay_states; Type: ROW SECURITY; Schema: auth; Owner: -
--

ALTER TABLE auth.saml_relay_states ENABLE ROW LEVEL SECURITY;

--
-- Name: schema_migrations; Type: ROW SECURITY; Schema: auth; Owner: -
--

ALTER TABLE auth.schema_migrations ENABLE ROW LEVEL SECURITY;

--
-- Name: sessions; Type: ROW SECURITY; Schema: auth; Owner: -
--

ALTER TABLE auth.sessions ENABLE ROW LEVEL SECURITY;

--
-- Name: sso_domains; Type: ROW SECURITY; Schema: auth; Owner: -
--

ALTER TABLE auth.sso_domains ENABLE ROW LEVEL SECURITY;

--
-- Name: sso_providers; Type: ROW SECURITY; Schema: auth; Owner: -
--

ALTER TABLE auth.sso_providers ENABLE ROW LEVEL SECURITY;

--
-- Name: users; Type: ROW SECURITY; Schema: auth; Owner: -
--

ALTER TABLE auth.users ENABLE ROW LEVEL SECURITY;

--
-- Name: shipping_providers Allow all for admin service; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Allow all for admin service" ON public.shipping_providers USING (true);


--
-- Name: product_analytics Allow insert analytics; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Allow insert analytics" ON public.product_analytics FOR INSERT WITH CHECK (true);


--
-- Name: coupon_usages Allow insert for authenticated users; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Allow insert for authenticated users" ON public.coupon_usages FOR INSERT WITH CHECK (true);


--
-- Name: user_roles Allow read own user_roles; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Allow read own user_roles" ON public.user_roles FOR SELECT USING (true);


--
-- Name: roles Allow read roles for all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Allow read roles for all" ON public.roles FOR SELECT USING (true);


--
-- Name: product_analytics Backend only write; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Backend only write" ON public.product_analytics USING ((auth.role() = 'service_role'::text));


--
-- Name: shipment_events Enable all access for all users; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Enable all access for all users" ON public.shipment_events USING (true) WITH CHECK (true);


--
-- Name: shipments Enable all access for all users; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Enable all access for all users" ON public.shipments USING (true) WITH CHECK (true);


--
-- Name: system_settings Enable all access for all users; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Enable all access for all users" ON public.system_settings USING (true) WITH CHECK (true);


--
-- Name: product_analytics Enable insert for all users; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "Enable insert for all users" ON public.product_analytics USING (true) WITH CHECK (true);


--
-- Name: product_analytics allow_insert_analytics; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY allow_insert_analytics ON public.product_analytics FOR INSERT WITH CHECK (true);


--
-- Name: audit_logs; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;

--
-- Name: brands; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.brands ENABLE ROW LEVEL SECURITY;

--
-- Name: carrier_status_mapping; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.carrier_status_mapping ENABLE ROW LEVEL SECURITY;

--
-- Name: coupon_segments; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.coupon_segments ENABLE ROW LEVEL SECURITY;

--
-- Name: coupon_usages; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.coupon_usages ENABLE ROW LEVEL SECURITY;

--
-- Name: flash_sale_items; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.flash_sale_items ENABLE ROW LEVEL SECURITY;

--
-- Name: flash_sales; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.flash_sales ENABLE ROW LEVEL SECURITY;

--
-- Name: inventory_logs; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.inventory_logs ENABLE ROW LEVEL SECURITY;

--
-- Name: payments; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.payments ENABLE ROW LEVEL SECURITY;

--
-- Name: permission_groups; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.permission_groups ENABLE ROW LEVEL SECURITY;

--
-- Name: permissions; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.permissions ENABLE ROW LEVEL SECURITY;

--
-- Name: product_analytics; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.product_analytics ENABLE ROW LEVEL SECURITY;

--
-- Name: product_reviews; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.product_reviews ENABLE ROW LEVEL SECURITY;

--
-- Name: role_permissions; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.role_permissions ENABLE ROW LEVEL SECURITY;

--
-- Name: shipment_events; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.shipment_events ENABLE ROW LEVEL SECURITY;

--
-- Name: shipments; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.shipments ENABLE ROW LEVEL SECURITY;

--
-- Name: shipping_configs; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.shipping_configs ENABLE ROW LEVEL SECURITY;

--
-- Name: system_settings; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.system_settings ENABLE ROW LEVEL SECURITY;

--
-- Name: tenants; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.tenants ENABLE ROW LEVEL SECURITY;

--
-- Name: user_permissions; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.user_permissions ENABLE ROW LEVEL SECURITY;

--
-- Name: webhook_logs; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.webhook_logs ENABLE ROW LEVEL SECURITY;

--
-- Name: messages; Type: ROW SECURITY; Schema: realtime; Owner: -
--

ALTER TABLE realtime.messages ENABLE ROW LEVEL SECURITY;

--
-- Name: buckets; Type: ROW SECURITY; Schema: storage; Owner: -
--

ALTER TABLE storage.buckets ENABLE ROW LEVEL SECURITY;

--
-- Name: buckets_analytics; Type: ROW SECURITY; Schema: storage; Owner: -
--

ALTER TABLE storage.buckets_analytics ENABLE ROW LEVEL SECURITY;

--
-- Name: buckets_vectors; Type: ROW SECURITY; Schema: storage; Owner: -
--

ALTER TABLE storage.buckets_vectors ENABLE ROW LEVEL SECURITY;

--
-- Name: migrations; Type: ROW SECURITY; Schema: storage; Owner: -
--

ALTER TABLE storage.migrations ENABLE ROW LEVEL SECURITY;

--
-- Name: objects; Type: ROW SECURITY; Schema: storage; Owner: -
--

ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY;

--
-- Name: s3_multipart_uploads; Type: ROW SECURITY; Schema: storage; Owner: -
--

ALTER TABLE storage.s3_multipart_uploads ENABLE ROW LEVEL SECURITY;

--
-- Name: s3_multipart_uploads_parts; Type: ROW SECURITY; Schema: storage; Owner: -
--

ALTER TABLE storage.s3_multipart_uploads_parts ENABLE ROW LEVEL SECURITY;

--
-- Name: vector_indexes; Type: ROW SECURITY; Schema: storage; Owner: -
--

ALTER TABLE storage.vector_indexes ENABLE ROW LEVEL SECURITY;

--
-- Name: supabase_realtime; Type: PUBLICATION; Schema: -; Owner: -
--

CREATE PUBLICATION supabase_realtime WITH (publish = 'insert, update, delete, truncate');


--
-- Name: SCHEMA auth; Type: ACL; Schema: -; Owner: -
--

GRANT USAGE ON SCHEMA auth TO anon;
GRANT USAGE ON SCHEMA auth TO authenticated;
GRANT USAGE ON SCHEMA auth TO service_role;
GRANT ALL ON SCHEMA auth TO supabase_auth_admin;
GRANT ALL ON SCHEMA auth TO dashboard_user;
GRANT USAGE ON SCHEMA auth TO postgres;


--
-- Name: SCHEMA extensions; Type: ACL; Schema: -; Owner: -
--

GRANT USAGE ON SCHEMA extensions TO anon;
GRANT USAGE ON SCHEMA extensions TO authenticated;
GRANT USAGE ON SCHEMA extensions TO service_role;
GRANT ALL ON SCHEMA extensions TO dashboard_user;


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: -
--

GRANT USAGE ON SCHEMA public TO postgres;
GRANT USAGE ON SCHEMA public TO anon;
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT USAGE ON SCHEMA public TO service_role;


--
-- Name: SCHEMA realtime; Type: ACL; Schema: -; Owner: -
--

GRANT USAGE ON SCHEMA realtime TO postgres;
GRANT USAGE ON SCHEMA realtime TO anon;
GRANT USAGE ON SCHEMA realtime TO authenticated;
GRANT USAGE ON SCHEMA realtime TO service_role;
GRANT ALL ON SCHEMA realtime TO supabase_realtime_admin;


--
-- Name: SCHEMA storage; Type: ACL; Schema: -; Owner: -
--

GRANT USAGE ON SCHEMA storage TO postgres WITH GRANT OPTION;
GRANT USAGE ON SCHEMA storage TO anon;
GRANT USAGE ON SCHEMA storage TO authenticated;
GRANT USAGE ON SCHEMA storage TO service_role;
GRANT ALL ON SCHEMA storage TO supabase_storage_admin WITH GRANT OPTION;
GRANT ALL ON SCHEMA storage TO dashboard_user;


--
-- Name: SCHEMA vault; Type: ACL; Schema: -; Owner: -
--

GRANT USAGE ON SCHEMA vault TO postgres WITH GRANT OPTION;
GRANT USAGE ON SCHEMA vault TO service_role;


--
-- Name: FUNCTION email(); Type: ACL; Schema: auth; Owner: -
--

GRANT ALL ON FUNCTION auth.email() TO dashboard_user;


--
-- Name: FUNCTION jwt(); Type: ACL; Schema: auth; Owner: -
--

GRANT ALL ON FUNCTION auth.jwt() TO postgres;
GRANT ALL ON FUNCTION auth.jwt() TO dashboard_user;


--
-- Name: FUNCTION role(); Type: ACL; Schema: auth; Owner: -
--

GRANT ALL ON FUNCTION auth.role() TO dashboard_user;


--
-- Name: FUNCTION uid(); Type: ACL; Schema: auth; Owner: -
--

GRANT ALL ON FUNCTION auth.uid() TO dashboard_user;


--
-- Name: FUNCTION armor(bytea); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.armor(bytea) FROM postgres;
GRANT ALL ON FUNCTION extensions.armor(bytea) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.armor(bytea) TO dashboard_user;


--
-- Name: FUNCTION armor(bytea, text[], text[]); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.armor(bytea, text[], text[]) FROM postgres;
GRANT ALL ON FUNCTION extensions.armor(bytea, text[], text[]) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.armor(bytea, text[], text[]) TO dashboard_user;


--
-- Name: FUNCTION crypt(text, text); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.crypt(text, text) FROM postgres;
GRANT ALL ON FUNCTION extensions.crypt(text, text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.crypt(text, text) TO dashboard_user;


--
-- Name: FUNCTION dearmor(text); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.dearmor(text) FROM postgres;
GRANT ALL ON FUNCTION extensions.dearmor(text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.dearmor(text) TO dashboard_user;


--
-- Name: FUNCTION decrypt(bytea, bytea, text); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.decrypt(bytea, bytea, text) FROM postgres;
GRANT ALL ON FUNCTION extensions.decrypt(bytea, bytea, text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.decrypt(bytea, bytea, text) TO dashboard_user;


--
-- Name: FUNCTION decrypt_iv(bytea, bytea, bytea, text); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.decrypt_iv(bytea, bytea, bytea, text) FROM postgres;
GRANT ALL ON FUNCTION extensions.decrypt_iv(bytea, bytea, bytea, text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.decrypt_iv(bytea, bytea, bytea, text) TO dashboard_user;


--
-- Name: FUNCTION digest(bytea, text); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.digest(bytea, text) FROM postgres;
GRANT ALL ON FUNCTION extensions.digest(bytea, text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.digest(bytea, text) TO dashboard_user;


--
-- Name: FUNCTION digest(text, text); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.digest(text, text) FROM postgres;
GRANT ALL ON FUNCTION extensions.digest(text, text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.digest(text, text) TO dashboard_user;


--
-- Name: FUNCTION encrypt(bytea, bytea, text); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.encrypt(bytea, bytea, text) FROM postgres;
GRANT ALL ON FUNCTION extensions.encrypt(bytea, bytea, text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.encrypt(bytea, bytea, text) TO dashboard_user;


--
-- Name: FUNCTION encrypt_iv(bytea, bytea, bytea, text); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.encrypt_iv(bytea, bytea, bytea, text) FROM postgres;
GRANT ALL ON FUNCTION extensions.encrypt_iv(bytea, bytea, bytea, text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.encrypt_iv(bytea, bytea, bytea, text) TO dashboard_user;


--
-- Name: FUNCTION gen_random_bytes(integer); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.gen_random_bytes(integer) FROM postgres;
GRANT ALL ON FUNCTION extensions.gen_random_bytes(integer) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.gen_random_bytes(integer) TO dashboard_user;


--
-- Name: FUNCTION gen_random_uuid(); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.gen_random_uuid() FROM postgres;
GRANT ALL ON FUNCTION extensions.gen_random_uuid() TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.gen_random_uuid() TO dashboard_user;


--
-- Name: FUNCTION gen_salt(text); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.gen_salt(text) FROM postgres;
GRANT ALL ON FUNCTION extensions.gen_salt(text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.gen_salt(text) TO dashboard_user;


--
-- Name: FUNCTION gen_salt(text, integer); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.gen_salt(text, integer) FROM postgres;
GRANT ALL ON FUNCTION extensions.gen_salt(text, integer) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.gen_salt(text, integer) TO dashboard_user;


--
-- Name: FUNCTION grant_pg_cron_access(); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.grant_pg_cron_access() FROM supabase_admin;
GRANT ALL ON FUNCTION extensions.grant_pg_cron_access() TO supabase_admin WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.grant_pg_cron_access() TO dashboard_user;


--
-- Name: FUNCTION grant_pg_graphql_access(); Type: ACL; Schema: extensions; Owner: -
--

GRANT ALL ON FUNCTION extensions.grant_pg_graphql_access() TO postgres WITH GRANT OPTION;


--
-- Name: FUNCTION grant_pg_net_access(); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.grant_pg_net_access() FROM supabase_admin;
GRANT ALL ON FUNCTION extensions.grant_pg_net_access() TO supabase_admin WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.grant_pg_net_access() TO dashboard_user;


--
-- Name: FUNCTION hmac(bytea, bytea, text); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.hmac(bytea, bytea, text) FROM postgres;
GRANT ALL ON FUNCTION extensions.hmac(bytea, bytea, text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.hmac(bytea, bytea, text) TO dashboard_user;


--
-- Name: FUNCTION hmac(text, text, text); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.hmac(text, text, text) FROM postgres;
GRANT ALL ON FUNCTION extensions.hmac(text, text, text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.hmac(text, text, text) TO dashboard_user;


--
-- Name: FUNCTION pg_stat_statements(showtext boolean, OUT userid oid, OUT dbid oid, OUT toplevel boolean, OUT queryid bigint, OUT query text, OUT plans bigint, OUT total_plan_time double precision, OUT min_plan_time double precision, OUT max_plan_time double precision, OUT mean_plan_time double precision, OUT stddev_plan_time double precision, OUT calls bigint, OUT total_exec_time double precision, OUT min_exec_time double precision, OUT max_exec_time double precision, OUT mean_exec_time double precision, OUT stddev_exec_time double precision, OUT rows bigint, OUT shared_blks_hit bigint, OUT shared_blks_read bigint, OUT shared_blks_dirtied bigint, OUT shared_blks_written bigint, OUT local_blks_hit bigint, OUT local_blks_read bigint, OUT local_blks_dirtied bigint, OUT local_blks_written bigint, OUT temp_blks_read bigint, OUT temp_blks_written bigint, OUT shared_blk_read_time double precision, OUT shared_blk_write_time double precision, OUT local_blk_read_time double precision, OUT local_blk_write_time double precision, OUT temp_blk_read_time double precision, OUT temp_blk_write_time double precision, OUT wal_records bigint, OUT wal_fpi bigint, OUT wal_bytes numeric, OUT jit_functions bigint, OUT jit_generation_time double precision, OUT jit_inlining_count bigint, OUT jit_inlining_time double precision, OUT jit_optimization_count bigint, OUT jit_optimization_time double precision, OUT jit_emission_count bigint, OUT jit_emission_time double precision, OUT jit_deform_count bigint, OUT jit_deform_time double precision, OUT stats_since timestamp with time zone, OUT minmax_stats_since timestamp with time zone); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.pg_stat_statements(showtext boolean, OUT userid oid, OUT dbid oid, OUT toplevel boolean, OUT queryid bigint, OUT query text, OUT plans bigint, OUT total_plan_time double precision, OUT min_plan_time double precision, OUT max_plan_time double precision, OUT mean_plan_time double precision, OUT stddev_plan_time double precision, OUT calls bigint, OUT total_exec_time double precision, OUT min_exec_time double precision, OUT max_exec_time double precision, OUT mean_exec_time double precision, OUT stddev_exec_time double precision, OUT rows bigint, OUT shared_blks_hit bigint, OUT shared_blks_read bigint, OUT shared_blks_dirtied bigint, OUT shared_blks_written bigint, OUT local_blks_hit bigint, OUT local_blks_read bigint, OUT local_blks_dirtied bigint, OUT local_blks_written bigint, OUT temp_blks_read bigint, OUT temp_blks_written bigint, OUT shared_blk_read_time double precision, OUT shared_blk_write_time double precision, OUT local_blk_read_time double precision, OUT local_blk_write_time double precision, OUT temp_blk_read_time double precision, OUT temp_blk_write_time double precision, OUT wal_records bigint, OUT wal_fpi bigint, OUT wal_bytes numeric, OUT jit_functions bigint, OUT jit_generation_time double precision, OUT jit_inlining_count bigint, OUT jit_inlining_time double precision, OUT jit_optimization_count bigint, OUT jit_optimization_time double precision, OUT jit_emission_count bigint, OUT jit_emission_time double precision, OUT jit_deform_count bigint, OUT jit_deform_time double precision, OUT stats_since timestamp with time zone, OUT minmax_stats_since timestamp with time zone) FROM postgres;
GRANT ALL ON FUNCTION extensions.pg_stat_statements(showtext boolean, OUT userid oid, OUT dbid oid, OUT toplevel boolean, OUT queryid bigint, OUT query text, OUT plans bigint, OUT total_plan_time double precision, OUT min_plan_time double precision, OUT max_plan_time double precision, OUT mean_plan_time double precision, OUT stddev_plan_time double precision, OUT calls bigint, OUT total_exec_time double precision, OUT min_exec_time double precision, OUT max_exec_time double precision, OUT mean_exec_time double precision, OUT stddev_exec_time double precision, OUT rows bigint, OUT shared_blks_hit bigint, OUT shared_blks_read bigint, OUT shared_blks_dirtied bigint, OUT shared_blks_written bigint, OUT local_blks_hit bigint, OUT local_blks_read bigint, OUT local_blks_dirtied bigint, OUT local_blks_written bigint, OUT temp_blks_read bigint, OUT temp_blks_written bigint, OUT shared_blk_read_time double precision, OUT shared_blk_write_time double precision, OUT local_blk_read_time double precision, OUT local_blk_write_time double precision, OUT temp_blk_read_time double precision, OUT temp_blk_write_time double precision, OUT wal_records bigint, OUT wal_fpi bigint, OUT wal_bytes numeric, OUT jit_functions bigint, OUT jit_generation_time double precision, OUT jit_inlining_count bigint, OUT jit_inlining_time double precision, OUT jit_optimization_count bigint, OUT jit_optimization_time double precision, OUT jit_emission_count bigint, OUT jit_emission_time double precision, OUT jit_deform_count bigint, OUT jit_deform_time double precision, OUT stats_since timestamp with time zone, OUT minmax_stats_since timestamp with time zone) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.pg_stat_statements(showtext boolean, OUT userid oid, OUT dbid oid, OUT toplevel boolean, OUT queryid bigint, OUT query text, OUT plans bigint, OUT total_plan_time double precision, OUT min_plan_time double precision, OUT max_plan_time double precision, OUT mean_plan_time double precision, OUT stddev_plan_time double precision, OUT calls bigint, OUT total_exec_time double precision, OUT min_exec_time double precision, OUT max_exec_time double precision, OUT mean_exec_time double precision, OUT stddev_exec_time double precision, OUT rows bigint, OUT shared_blks_hit bigint, OUT shared_blks_read bigint, OUT shared_blks_dirtied bigint, OUT shared_blks_written bigint, OUT local_blks_hit bigint, OUT local_blks_read bigint, OUT local_blks_dirtied bigint, OUT local_blks_written bigint, OUT temp_blks_read bigint, OUT temp_blks_written bigint, OUT shared_blk_read_time double precision, OUT shared_blk_write_time double precision, OUT local_blk_read_time double precision, OUT local_blk_write_time double precision, OUT temp_blk_read_time double precision, OUT temp_blk_write_time double precision, OUT wal_records bigint, OUT wal_fpi bigint, OUT wal_bytes numeric, OUT jit_functions bigint, OUT jit_generation_time double precision, OUT jit_inlining_count bigint, OUT jit_inlining_time double precision, OUT jit_optimization_count bigint, OUT jit_optimization_time double precision, OUT jit_emission_count bigint, OUT jit_emission_time double precision, OUT jit_deform_count bigint, OUT jit_deform_time double precision, OUT stats_since timestamp with time zone, OUT minmax_stats_since timestamp with time zone) TO dashboard_user;


--
-- Name: FUNCTION pg_stat_statements_info(OUT dealloc bigint, OUT stats_reset timestamp with time zone); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.pg_stat_statements_info(OUT dealloc bigint, OUT stats_reset timestamp with time zone) FROM postgres;
GRANT ALL ON FUNCTION extensions.pg_stat_statements_info(OUT dealloc bigint, OUT stats_reset timestamp with time zone) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.pg_stat_statements_info(OUT dealloc bigint, OUT stats_reset timestamp with time zone) TO dashboard_user;


--
-- Name: FUNCTION pg_stat_statements_reset(userid oid, dbid oid, queryid bigint, minmax_only boolean); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.pg_stat_statements_reset(userid oid, dbid oid, queryid bigint, minmax_only boolean) FROM postgres;
GRANT ALL ON FUNCTION extensions.pg_stat_statements_reset(userid oid, dbid oid, queryid bigint, minmax_only boolean) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.pg_stat_statements_reset(userid oid, dbid oid, queryid bigint, minmax_only boolean) TO dashboard_user;


--
-- Name: FUNCTION pgp_armor_headers(text, OUT key text, OUT value text); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.pgp_armor_headers(text, OUT key text, OUT value text) FROM postgres;
GRANT ALL ON FUNCTION extensions.pgp_armor_headers(text, OUT key text, OUT value text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.pgp_armor_headers(text, OUT key text, OUT value text) TO dashboard_user;


--
-- Name: FUNCTION pgp_key_id(bytea); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.pgp_key_id(bytea) FROM postgres;
GRANT ALL ON FUNCTION extensions.pgp_key_id(bytea) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.pgp_key_id(bytea) TO dashboard_user;


--
-- Name: FUNCTION pgp_pub_decrypt(bytea, bytea); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.pgp_pub_decrypt(bytea, bytea) FROM postgres;
GRANT ALL ON FUNCTION extensions.pgp_pub_decrypt(bytea, bytea) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.pgp_pub_decrypt(bytea, bytea) TO dashboard_user;


--
-- Name: FUNCTION pgp_pub_decrypt(bytea, bytea, text); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.pgp_pub_decrypt(bytea, bytea, text) FROM postgres;
GRANT ALL ON FUNCTION extensions.pgp_pub_decrypt(bytea, bytea, text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.pgp_pub_decrypt(bytea, bytea, text) TO dashboard_user;


--
-- Name: FUNCTION pgp_pub_decrypt(bytea, bytea, text, text); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.pgp_pub_decrypt(bytea, bytea, text, text) FROM postgres;
GRANT ALL ON FUNCTION extensions.pgp_pub_decrypt(bytea, bytea, text, text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.pgp_pub_decrypt(bytea, bytea, text, text) TO dashboard_user;


--
-- Name: FUNCTION pgp_pub_decrypt_bytea(bytea, bytea); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.pgp_pub_decrypt_bytea(bytea, bytea) FROM postgres;
GRANT ALL ON FUNCTION extensions.pgp_pub_decrypt_bytea(bytea, bytea) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.pgp_pub_decrypt_bytea(bytea, bytea) TO dashboard_user;


--
-- Name: FUNCTION pgp_pub_decrypt_bytea(bytea, bytea, text); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.pgp_pub_decrypt_bytea(bytea, bytea, text) FROM postgres;
GRANT ALL ON FUNCTION extensions.pgp_pub_decrypt_bytea(bytea, bytea, text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.pgp_pub_decrypt_bytea(bytea, bytea, text) TO dashboard_user;


--
-- Name: FUNCTION pgp_pub_decrypt_bytea(bytea, bytea, text, text); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.pgp_pub_decrypt_bytea(bytea, bytea, text, text) FROM postgres;
GRANT ALL ON FUNCTION extensions.pgp_pub_decrypt_bytea(bytea, bytea, text, text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.pgp_pub_decrypt_bytea(bytea, bytea, text, text) TO dashboard_user;


--
-- Name: FUNCTION pgp_pub_encrypt(text, bytea); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.pgp_pub_encrypt(text, bytea) FROM postgres;
GRANT ALL ON FUNCTION extensions.pgp_pub_encrypt(text, bytea) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.pgp_pub_encrypt(text, bytea) TO dashboard_user;


--
-- Name: FUNCTION pgp_pub_encrypt(text, bytea, text); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.pgp_pub_encrypt(text, bytea, text) FROM postgres;
GRANT ALL ON FUNCTION extensions.pgp_pub_encrypt(text, bytea, text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.pgp_pub_encrypt(text, bytea, text) TO dashboard_user;


--
-- Name: FUNCTION pgp_pub_encrypt_bytea(bytea, bytea); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.pgp_pub_encrypt_bytea(bytea, bytea) FROM postgres;
GRANT ALL ON FUNCTION extensions.pgp_pub_encrypt_bytea(bytea, bytea) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.pgp_pub_encrypt_bytea(bytea, bytea) TO dashboard_user;


--
-- Name: FUNCTION pgp_pub_encrypt_bytea(bytea, bytea, text); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.pgp_pub_encrypt_bytea(bytea, bytea, text) FROM postgres;
GRANT ALL ON FUNCTION extensions.pgp_pub_encrypt_bytea(bytea, bytea, text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.pgp_pub_encrypt_bytea(bytea, bytea, text) TO dashboard_user;


--
-- Name: FUNCTION pgp_sym_decrypt(bytea, text); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.pgp_sym_decrypt(bytea, text) FROM postgres;
GRANT ALL ON FUNCTION extensions.pgp_sym_decrypt(bytea, text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.pgp_sym_decrypt(bytea, text) TO dashboard_user;


--
-- Name: FUNCTION pgp_sym_decrypt(bytea, text, text); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.pgp_sym_decrypt(bytea, text, text) FROM postgres;
GRANT ALL ON FUNCTION extensions.pgp_sym_decrypt(bytea, text, text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.pgp_sym_decrypt(bytea, text, text) TO dashboard_user;


--
-- Name: FUNCTION pgp_sym_decrypt_bytea(bytea, text); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.pgp_sym_decrypt_bytea(bytea, text) FROM postgres;
GRANT ALL ON FUNCTION extensions.pgp_sym_decrypt_bytea(bytea, text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.pgp_sym_decrypt_bytea(bytea, text) TO dashboard_user;


--
-- Name: FUNCTION pgp_sym_decrypt_bytea(bytea, text, text); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.pgp_sym_decrypt_bytea(bytea, text, text) FROM postgres;
GRANT ALL ON FUNCTION extensions.pgp_sym_decrypt_bytea(bytea, text, text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.pgp_sym_decrypt_bytea(bytea, text, text) TO dashboard_user;


--
-- Name: FUNCTION pgp_sym_encrypt(text, text); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.pgp_sym_encrypt(text, text) FROM postgres;
GRANT ALL ON FUNCTION extensions.pgp_sym_encrypt(text, text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.pgp_sym_encrypt(text, text) TO dashboard_user;


--
-- Name: FUNCTION pgp_sym_encrypt(text, text, text); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.pgp_sym_encrypt(text, text, text) FROM postgres;
GRANT ALL ON FUNCTION extensions.pgp_sym_encrypt(text, text, text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.pgp_sym_encrypt(text, text, text) TO dashboard_user;


--
-- Name: FUNCTION pgp_sym_encrypt_bytea(bytea, text); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.pgp_sym_encrypt_bytea(bytea, text) FROM postgres;
GRANT ALL ON FUNCTION extensions.pgp_sym_encrypt_bytea(bytea, text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.pgp_sym_encrypt_bytea(bytea, text) TO dashboard_user;


--
-- Name: FUNCTION pgp_sym_encrypt_bytea(bytea, text, text); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.pgp_sym_encrypt_bytea(bytea, text, text) FROM postgres;
GRANT ALL ON FUNCTION extensions.pgp_sym_encrypt_bytea(bytea, text, text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.pgp_sym_encrypt_bytea(bytea, text, text) TO dashboard_user;


--
-- Name: FUNCTION pgrst_ddl_watch(); Type: ACL; Schema: extensions; Owner: -
--

GRANT ALL ON FUNCTION extensions.pgrst_ddl_watch() TO postgres WITH GRANT OPTION;


--
-- Name: FUNCTION pgrst_drop_watch(); Type: ACL; Schema: extensions; Owner: -
--

GRANT ALL ON FUNCTION extensions.pgrst_drop_watch() TO postgres WITH GRANT OPTION;


--
-- Name: FUNCTION set_graphql_placeholder(); Type: ACL; Schema: extensions; Owner: -
--

GRANT ALL ON FUNCTION extensions.set_graphql_placeholder() TO postgres WITH GRANT OPTION;


--
-- Name: FUNCTION uuid_generate_v1(); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.uuid_generate_v1() FROM postgres;
GRANT ALL ON FUNCTION extensions.uuid_generate_v1() TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.uuid_generate_v1() TO dashboard_user;


--
-- Name: FUNCTION uuid_generate_v1mc(); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.uuid_generate_v1mc() FROM postgres;
GRANT ALL ON FUNCTION extensions.uuid_generate_v1mc() TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.uuid_generate_v1mc() TO dashboard_user;


--
-- Name: FUNCTION uuid_generate_v3(namespace uuid, name text); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.uuid_generate_v3(namespace uuid, name text) FROM postgres;
GRANT ALL ON FUNCTION extensions.uuid_generate_v3(namespace uuid, name text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.uuid_generate_v3(namespace uuid, name text) TO dashboard_user;


--
-- Name: FUNCTION uuid_generate_v4(); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.uuid_generate_v4() FROM postgres;
GRANT ALL ON FUNCTION extensions.uuid_generate_v4() TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.uuid_generate_v4() TO dashboard_user;


--
-- Name: FUNCTION uuid_generate_v5(namespace uuid, name text); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.uuid_generate_v5(namespace uuid, name text) FROM postgres;
GRANT ALL ON FUNCTION extensions.uuid_generate_v5(namespace uuid, name text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.uuid_generate_v5(namespace uuid, name text) TO dashboard_user;


--
-- Name: FUNCTION uuid_nil(); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.uuid_nil() FROM postgres;
GRANT ALL ON FUNCTION extensions.uuid_nil() TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.uuid_nil() TO dashboard_user;


--
-- Name: FUNCTION uuid_ns_dns(); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.uuid_ns_dns() FROM postgres;
GRANT ALL ON FUNCTION extensions.uuid_ns_dns() TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.uuid_ns_dns() TO dashboard_user;


--
-- Name: FUNCTION uuid_ns_oid(); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.uuid_ns_oid() FROM postgres;
GRANT ALL ON FUNCTION extensions.uuid_ns_oid() TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.uuid_ns_oid() TO dashboard_user;


--
-- Name: FUNCTION uuid_ns_url(); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.uuid_ns_url() FROM postgres;
GRANT ALL ON FUNCTION extensions.uuid_ns_url() TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.uuid_ns_url() TO dashboard_user;


--
-- Name: FUNCTION uuid_ns_x500(); Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON FUNCTION extensions.uuid_ns_x500() FROM postgres;
GRANT ALL ON FUNCTION extensions.uuid_ns_x500() TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.uuid_ns_x500() TO dashboard_user;


--
-- Name: FUNCTION graphql("operationName" text, query text, variables jsonb, extensions jsonb); Type: ACL; Schema: graphql_public; Owner: -
--

GRANT ALL ON FUNCTION graphql_public.graphql("operationName" text, query text, variables jsonb, extensions jsonb) TO postgres;
GRANT ALL ON FUNCTION graphql_public.graphql("operationName" text, query text, variables jsonb, extensions jsonb) TO anon;
GRANT ALL ON FUNCTION graphql_public.graphql("operationName" text, query text, variables jsonb, extensions jsonb) TO authenticated;
GRANT ALL ON FUNCTION graphql_public.graphql("operationName" text, query text, variables jsonb, extensions jsonb) TO service_role;


--
-- Name: FUNCTION pg_reload_conf(); Type: ACL; Schema: pg_catalog; Owner: -
--

GRANT ALL ON FUNCTION pg_catalog.pg_reload_conf() TO postgres WITH GRANT OPTION;


--
-- Name: FUNCTION get_auth(p_usename text); Type: ACL; Schema: pgbouncer; Owner: -
--

REVOKE ALL ON FUNCTION pgbouncer.get_auth(p_usename text) FROM PUBLIC;
GRANT ALL ON FUNCTION pgbouncer.get_auth(p_usename text) TO pgbouncer;


--
-- Name: FUNCTION add_item_to_cart(p_user_id uuid, p_product_id uuid, p_quantity integer, p_size text); Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON FUNCTION public.add_item_to_cart(p_user_id uuid, p_product_id uuid, p_quantity integer, p_size text) TO anon;
GRANT ALL ON FUNCTION public.add_item_to_cart(p_user_id uuid, p_product_id uuid, p_quantity integer, p_size text) TO authenticated;
GRANT ALL ON FUNCTION public.add_item_to_cart(p_user_id uuid, p_product_id uuid, p_quantity integer, p_size text) TO service_role;


--
-- Name: FUNCTION apply_coupon(p_code text, p_user_id uuid, p_order_id uuid); Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON FUNCTION public.apply_coupon(p_code text, p_user_id uuid, p_order_id uuid) TO anon;
GRANT ALL ON FUNCTION public.apply_coupon(p_code text, p_user_id uuid, p_order_id uuid) TO authenticated;
GRANT ALL ON FUNCTION public.apply_coupon(p_code text, p_user_id uuid, p_order_id uuid) TO service_role;


--
-- Name: FUNCTION get_cart_total_quantity(p_user_id uuid); Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON FUNCTION public.get_cart_total_quantity(p_user_id uuid) TO anon;
GRANT ALL ON FUNCTION public.get_cart_total_quantity(p_user_id uuid) TO authenticated;
GRANT ALL ON FUNCTION public.get_cart_total_quantity(p_user_id uuid) TO service_role;


--
-- Name: FUNCTION get_product_count_by_category(); Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON FUNCTION public.get_product_count_by_category() TO anon;
GRANT ALL ON FUNCTION public.get_product_count_by_category() TO authenticated;
GRANT ALL ON FUNCTION public.get_product_count_by_category() TO service_role;


--
-- Name: FUNCTION is_user_in_segment(p_user_id uuid, p_segment text); Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON FUNCTION public.is_user_in_segment(p_user_id uuid, p_segment text) TO anon;
GRANT ALL ON FUNCTION public.is_user_in_segment(p_user_id uuid, p_segment text) TO authenticated;
GRANT ALL ON FUNCTION public.is_user_in_segment(p_user_id uuid, p_segment text) TO service_role;


--
-- Name: FUNCTION log_product_event(p_product_id uuid, p_channel text, p_source text, p_event_type text, p_revenue numeric, p_qty integer); Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON FUNCTION public.log_product_event(p_product_id uuid, p_channel text, p_source text, p_event_type text, p_revenue numeric, p_qty integer) TO anon;
GRANT ALL ON FUNCTION public.log_product_event(p_product_id uuid, p_channel text, p_source text, p_event_type text, p_revenue numeric, p_qty integer) TO authenticated;
GRANT ALL ON FUNCTION public.log_product_event(p_product_id uuid, p_channel text, p_source text, p_event_type text, p_revenue numeric, p_qty integer) TO service_role;


--
-- Name: FUNCTION rls_auto_enable(); Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON FUNCTION public.rls_auto_enable() TO anon;
GRANT ALL ON FUNCTION public.rls_auto_enable() TO authenticated;
GRANT ALL ON FUNCTION public.rls_auto_enable() TO service_role;


--
-- Name: FUNCTION update_modified_column(); Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON FUNCTION public.update_modified_column() TO anon;
GRANT ALL ON FUNCTION public.update_modified_column() TO authenticated;
GRANT ALL ON FUNCTION public.update_modified_column() TO service_role;


--
-- Name: FUNCTION update_updated_at_column(); Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON FUNCTION public.update_updated_at_column() TO anon;
GRANT ALL ON FUNCTION public.update_updated_at_column() TO authenticated;
GRANT ALL ON FUNCTION public.update_updated_at_column() TO service_role;


--
-- Name: FUNCTION apply_rls(wal jsonb, max_record_bytes integer); Type: ACL; Schema: realtime; Owner: -
--

GRANT ALL ON FUNCTION realtime.apply_rls(wal jsonb, max_record_bytes integer) TO postgres;
GRANT ALL ON FUNCTION realtime.apply_rls(wal jsonb, max_record_bytes integer) TO dashboard_user;
GRANT ALL ON FUNCTION realtime.apply_rls(wal jsonb, max_record_bytes integer) TO anon;
GRANT ALL ON FUNCTION realtime.apply_rls(wal jsonb, max_record_bytes integer) TO authenticated;
GRANT ALL ON FUNCTION realtime.apply_rls(wal jsonb, max_record_bytes integer) TO service_role;
GRANT ALL ON FUNCTION realtime.apply_rls(wal jsonb, max_record_bytes integer) TO supabase_realtime_admin;


--
-- Name: FUNCTION broadcast_changes(topic_name text, event_name text, operation text, table_name text, table_schema text, new record, old record, level text); Type: ACL; Schema: realtime; Owner: -
--

GRANT ALL ON FUNCTION realtime.broadcast_changes(topic_name text, event_name text, operation text, table_name text, table_schema text, new record, old record, level text) TO postgres;
GRANT ALL ON FUNCTION realtime.broadcast_changes(topic_name text, event_name text, operation text, table_name text, table_schema text, new record, old record, level text) TO dashboard_user;


--
-- Name: FUNCTION build_prepared_statement_sql(prepared_statement_name text, entity regclass, columns realtime.wal_column[]); Type: ACL; Schema: realtime; Owner: -
--

GRANT ALL ON FUNCTION realtime.build_prepared_statement_sql(prepared_statement_name text, entity regclass, columns realtime.wal_column[]) TO postgres;
GRANT ALL ON FUNCTION realtime.build_prepared_statement_sql(prepared_statement_name text, entity regclass, columns realtime.wal_column[]) TO dashboard_user;
GRANT ALL ON FUNCTION realtime.build_prepared_statement_sql(prepared_statement_name text, entity regclass, columns realtime.wal_column[]) TO anon;
GRANT ALL ON FUNCTION realtime.build_prepared_statement_sql(prepared_statement_name text, entity regclass, columns realtime.wal_column[]) TO authenticated;
GRANT ALL ON FUNCTION realtime.build_prepared_statement_sql(prepared_statement_name text, entity regclass, columns realtime.wal_column[]) TO service_role;
GRANT ALL ON FUNCTION realtime.build_prepared_statement_sql(prepared_statement_name text, entity regclass, columns realtime.wal_column[]) TO supabase_realtime_admin;


--
-- Name: FUNCTION "cast"(val text, type_ regtype); Type: ACL; Schema: realtime; Owner: -
--

GRANT ALL ON FUNCTION realtime."cast"(val text, type_ regtype) TO postgres;
GRANT ALL ON FUNCTION realtime."cast"(val text, type_ regtype) TO dashboard_user;
GRANT ALL ON FUNCTION realtime."cast"(val text, type_ regtype) TO anon;
GRANT ALL ON FUNCTION realtime."cast"(val text, type_ regtype) TO authenticated;
GRANT ALL ON FUNCTION realtime."cast"(val text, type_ regtype) TO service_role;
GRANT ALL ON FUNCTION realtime."cast"(val text, type_ regtype) TO supabase_realtime_admin;


--
-- Name: FUNCTION check_equality_op(op realtime.equality_op, type_ regtype, val_1 text, val_2 text); Type: ACL; Schema: realtime; Owner: -
--

GRANT ALL ON FUNCTION realtime.check_equality_op(op realtime.equality_op, type_ regtype, val_1 text, val_2 text) TO postgres;
GRANT ALL ON FUNCTION realtime.check_equality_op(op realtime.equality_op, type_ regtype, val_1 text, val_2 text) TO dashboard_user;
GRANT ALL ON FUNCTION realtime.check_equality_op(op realtime.equality_op, type_ regtype, val_1 text, val_2 text) TO anon;
GRANT ALL ON FUNCTION realtime.check_equality_op(op realtime.equality_op, type_ regtype, val_1 text, val_2 text) TO authenticated;
GRANT ALL ON FUNCTION realtime.check_equality_op(op realtime.equality_op, type_ regtype, val_1 text, val_2 text) TO service_role;
GRANT ALL ON FUNCTION realtime.check_equality_op(op realtime.equality_op, type_ regtype, val_1 text, val_2 text) TO supabase_realtime_admin;


--
-- Name: FUNCTION is_visible_through_filters(columns realtime.wal_column[], filters realtime.user_defined_filter[]); Type: ACL; Schema: realtime; Owner: -
--

GRANT ALL ON FUNCTION realtime.is_visible_through_filters(columns realtime.wal_column[], filters realtime.user_defined_filter[]) TO postgres;
GRANT ALL ON FUNCTION realtime.is_visible_through_filters(columns realtime.wal_column[], filters realtime.user_defined_filter[]) TO dashboard_user;
GRANT ALL ON FUNCTION realtime.is_visible_through_filters(columns realtime.wal_column[], filters realtime.user_defined_filter[]) TO anon;
GRANT ALL ON FUNCTION realtime.is_visible_through_filters(columns realtime.wal_column[], filters realtime.user_defined_filter[]) TO authenticated;
GRANT ALL ON FUNCTION realtime.is_visible_through_filters(columns realtime.wal_column[], filters realtime.user_defined_filter[]) TO service_role;
GRANT ALL ON FUNCTION realtime.is_visible_through_filters(columns realtime.wal_column[], filters realtime.user_defined_filter[]) TO supabase_realtime_admin;


--
-- Name: FUNCTION list_changes(publication name, slot_name name, max_changes integer, max_record_bytes integer); Type: ACL; Schema: realtime; Owner: -
--

GRANT ALL ON FUNCTION realtime.list_changes(publication name, slot_name name, max_changes integer, max_record_bytes integer) TO postgres;
GRANT ALL ON FUNCTION realtime.list_changes(publication name, slot_name name, max_changes integer, max_record_bytes integer) TO dashboard_user;


--
-- Name: FUNCTION quote_wal2json(entity regclass); Type: ACL; Schema: realtime; Owner: -
--

GRANT ALL ON FUNCTION realtime.quote_wal2json(entity regclass) TO postgres;
GRANT ALL ON FUNCTION realtime.quote_wal2json(entity regclass) TO dashboard_user;
GRANT ALL ON FUNCTION realtime.quote_wal2json(entity regclass) TO anon;
GRANT ALL ON FUNCTION realtime.quote_wal2json(entity regclass) TO authenticated;
GRANT ALL ON FUNCTION realtime.quote_wal2json(entity regclass) TO service_role;
GRANT ALL ON FUNCTION realtime.quote_wal2json(entity regclass) TO supabase_realtime_admin;


--
-- Name: FUNCTION send(payload jsonb, event text, topic text, private boolean); Type: ACL; Schema: realtime; Owner: -
--

GRANT ALL ON FUNCTION realtime.send(payload jsonb, event text, topic text, private boolean) TO postgres;
GRANT ALL ON FUNCTION realtime.send(payload jsonb, event text, topic text, private boolean) TO dashboard_user;


--
-- Name: FUNCTION subscription_check_filters(); Type: ACL; Schema: realtime; Owner: -
--

GRANT ALL ON FUNCTION realtime.subscription_check_filters() TO postgres;
GRANT ALL ON FUNCTION realtime.subscription_check_filters() TO dashboard_user;
GRANT ALL ON FUNCTION realtime.subscription_check_filters() TO anon;
GRANT ALL ON FUNCTION realtime.subscription_check_filters() TO authenticated;
GRANT ALL ON FUNCTION realtime.subscription_check_filters() TO service_role;
GRANT ALL ON FUNCTION realtime.subscription_check_filters() TO supabase_realtime_admin;


--
-- Name: FUNCTION to_regrole(role_name text); Type: ACL; Schema: realtime; Owner: -
--

GRANT ALL ON FUNCTION realtime.to_regrole(role_name text) TO postgres;
GRANT ALL ON FUNCTION realtime.to_regrole(role_name text) TO dashboard_user;
GRANT ALL ON FUNCTION realtime.to_regrole(role_name text) TO anon;
GRANT ALL ON FUNCTION realtime.to_regrole(role_name text) TO authenticated;
GRANT ALL ON FUNCTION realtime.to_regrole(role_name text) TO service_role;
GRANT ALL ON FUNCTION realtime.to_regrole(role_name text) TO supabase_realtime_admin;


--
-- Name: FUNCTION topic(); Type: ACL; Schema: realtime; Owner: -
--

GRANT ALL ON FUNCTION realtime.topic() TO postgres;
GRANT ALL ON FUNCTION realtime.topic() TO dashboard_user;


--
-- Name: FUNCTION _crypto_aead_det_decrypt(message bytea, additional bytea, key_id bigint, context bytea, nonce bytea); Type: ACL; Schema: vault; Owner: -
--

GRANT ALL ON FUNCTION vault._crypto_aead_det_decrypt(message bytea, additional bytea, key_id bigint, context bytea, nonce bytea) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION vault._crypto_aead_det_decrypt(message bytea, additional bytea, key_id bigint, context bytea, nonce bytea) TO service_role;


--
-- Name: FUNCTION create_secret(new_secret text, new_name text, new_description text, new_key_id uuid); Type: ACL; Schema: vault; Owner: -
--

GRANT ALL ON FUNCTION vault.create_secret(new_secret text, new_name text, new_description text, new_key_id uuid) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION vault.create_secret(new_secret text, new_name text, new_description text, new_key_id uuid) TO service_role;


--
-- Name: FUNCTION update_secret(secret_id uuid, new_secret text, new_name text, new_description text, new_key_id uuid); Type: ACL; Schema: vault; Owner: -
--

GRANT ALL ON FUNCTION vault.update_secret(secret_id uuid, new_secret text, new_name text, new_description text, new_key_id uuid) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION vault.update_secret(secret_id uuid, new_secret text, new_name text, new_description text, new_key_id uuid) TO service_role;


--
-- Name: TABLE audit_log_entries; Type: ACL; Schema: auth; Owner: -
--

GRANT ALL ON TABLE auth.audit_log_entries TO dashboard_user;
GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,MAINTAIN,UPDATE ON TABLE auth.audit_log_entries TO postgres;
GRANT SELECT ON TABLE auth.audit_log_entries TO postgres WITH GRANT OPTION;


--
-- Name: TABLE custom_oauth_providers; Type: ACL; Schema: auth; Owner: -
--

GRANT ALL ON TABLE auth.custom_oauth_providers TO postgres;
GRANT ALL ON TABLE auth.custom_oauth_providers TO dashboard_user;


--
-- Name: TABLE flow_state; Type: ACL; Schema: auth; Owner: -
--

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,MAINTAIN,UPDATE ON TABLE auth.flow_state TO postgres;
GRANT SELECT ON TABLE auth.flow_state TO postgres WITH GRANT OPTION;
GRANT ALL ON TABLE auth.flow_state TO dashboard_user;


--
-- Name: TABLE identities; Type: ACL; Schema: auth; Owner: -
--

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,MAINTAIN,UPDATE ON TABLE auth.identities TO postgres;
GRANT SELECT ON TABLE auth.identities TO postgres WITH GRANT OPTION;
GRANT ALL ON TABLE auth.identities TO dashboard_user;


--
-- Name: TABLE instances; Type: ACL; Schema: auth; Owner: -
--

GRANT ALL ON TABLE auth.instances TO dashboard_user;
GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,MAINTAIN,UPDATE ON TABLE auth.instances TO postgres;
GRANT SELECT ON TABLE auth.instances TO postgres WITH GRANT OPTION;


--
-- Name: TABLE mfa_amr_claims; Type: ACL; Schema: auth; Owner: -
--

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,MAINTAIN,UPDATE ON TABLE auth.mfa_amr_claims TO postgres;
GRANT SELECT ON TABLE auth.mfa_amr_claims TO postgres WITH GRANT OPTION;
GRANT ALL ON TABLE auth.mfa_amr_claims TO dashboard_user;


--
-- Name: TABLE mfa_challenges; Type: ACL; Schema: auth; Owner: -
--

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,MAINTAIN,UPDATE ON TABLE auth.mfa_challenges TO postgres;
GRANT SELECT ON TABLE auth.mfa_challenges TO postgres WITH GRANT OPTION;
GRANT ALL ON TABLE auth.mfa_challenges TO dashboard_user;


--
-- Name: TABLE mfa_factors; Type: ACL; Schema: auth; Owner: -
--

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,MAINTAIN,UPDATE ON TABLE auth.mfa_factors TO postgres;
GRANT SELECT ON TABLE auth.mfa_factors TO postgres WITH GRANT OPTION;
GRANT ALL ON TABLE auth.mfa_factors TO dashboard_user;


--
-- Name: TABLE oauth_authorizations; Type: ACL; Schema: auth; Owner: -
--

GRANT ALL ON TABLE auth.oauth_authorizations TO postgres;
GRANT ALL ON TABLE auth.oauth_authorizations TO dashboard_user;


--
-- Name: TABLE oauth_client_states; Type: ACL; Schema: auth; Owner: -
--

GRANT ALL ON TABLE auth.oauth_client_states TO postgres;
GRANT ALL ON TABLE auth.oauth_client_states TO dashboard_user;


--
-- Name: TABLE oauth_clients; Type: ACL; Schema: auth; Owner: -
--

GRANT ALL ON TABLE auth.oauth_clients TO postgres;
GRANT ALL ON TABLE auth.oauth_clients TO dashboard_user;


--
-- Name: TABLE oauth_consents; Type: ACL; Schema: auth; Owner: -
--

GRANT ALL ON TABLE auth.oauth_consents TO postgres;
GRANT ALL ON TABLE auth.oauth_consents TO dashboard_user;


--
-- Name: TABLE one_time_tokens; Type: ACL; Schema: auth; Owner: -
--

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,MAINTAIN,UPDATE ON TABLE auth.one_time_tokens TO postgres;
GRANT SELECT ON TABLE auth.one_time_tokens TO postgres WITH GRANT OPTION;
GRANT ALL ON TABLE auth.one_time_tokens TO dashboard_user;


--
-- Name: TABLE refresh_tokens; Type: ACL; Schema: auth; Owner: -
--

GRANT ALL ON TABLE auth.refresh_tokens TO dashboard_user;
GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,MAINTAIN,UPDATE ON TABLE auth.refresh_tokens TO postgres;
GRANT SELECT ON TABLE auth.refresh_tokens TO postgres WITH GRANT OPTION;


--
-- Name: SEQUENCE refresh_tokens_id_seq; Type: ACL; Schema: auth; Owner: -
--

GRANT ALL ON SEQUENCE auth.refresh_tokens_id_seq TO dashboard_user;
GRANT ALL ON SEQUENCE auth.refresh_tokens_id_seq TO postgres;


--
-- Name: TABLE saml_providers; Type: ACL; Schema: auth; Owner: -
--

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,MAINTAIN,UPDATE ON TABLE auth.saml_providers TO postgres;
GRANT SELECT ON TABLE auth.saml_providers TO postgres WITH GRANT OPTION;
GRANT ALL ON TABLE auth.saml_providers TO dashboard_user;


--
-- Name: TABLE saml_relay_states; Type: ACL; Schema: auth; Owner: -
--

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,MAINTAIN,UPDATE ON TABLE auth.saml_relay_states TO postgres;
GRANT SELECT ON TABLE auth.saml_relay_states TO postgres WITH GRANT OPTION;
GRANT ALL ON TABLE auth.saml_relay_states TO dashboard_user;


--
-- Name: TABLE schema_migrations; Type: ACL; Schema: auth; Owner: -
--

GRANT SELECT ON TABLE auth.schema_migrations TO postgres WITH GRANT OPTION;


--
-- Name: TABLE sessions; Type: ACL; Schema: auth; Owner: -
--

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,MAINTAIN,UPDATE ON TABLE auth.sessions TO postgres;
GRANT SELECT ON TABLE auth.sessions TO postgres WITH GRANT OPTION;
GRANT ALL ON TABLE auth.sessions TO dashboard_user;


--
-- Name: TABLE sso_domains; Type: ACL; Schema: auth; Owner: -
--

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,MAINTAIN,UPDATE ON TABLE auth.sso_domains TO postgres;
GRANT SELECT ON TABLE auth.sso_domains TO postgres WITH GRANT OPTION;
GRANT ALL ON TABLE auth.sso_domains TO dashboard_user;


--
-- Name: TABLE sso_providers; Type: ACL; Schema: auth; Owner: -
--

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,MAINTAIN,UPDATE ON TABLE auth.sso_providers TO postgres;
GRANT SELECT ON TABLE auth.sso_providers TO postgres WITH GRANT OPTION;
GRANT ALL ON TABLE auth.sso_providers TO dashboard_user;


--
-- Name: TABLE users; Type: ACL; Schema: auth; Owner: -
--

GRANT ALL ON TABLE auth.users TO dashboard_user;
GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,MAINTAIN,UPDATE ON TABLE auth.users TO postgres;
GRANT SELECT ON TABLE auth.users TO postgres WITH GRANT OPTION;


--
-- Name: TABLE webauthn_challenges; Type: ACL; Schema: auth; Owner: -
--

GRANT ALL ON TABLE auth.webauthn_challenges TO postgres;
GRANT ALL ON TABLE auth.webauthn_challenges TO dashboard_user;


--
-- Name: TABLE webauthn_credentials; Type: ACL; Schema: auth; Owner: -
--

GRANT ALL ON TABLE auth.webauthn_credentials TO postgres;
GRANT ALL ON TABLE auth.webauthn_credentials TO dashboard_user;


--
-- Name: TABLE pg_stat_statements; Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON TABLE extensions.pg_stat_statements FROM postgres;
GRANT ALL ON TABLE extensions.pg_stat_statements TO postgres WITH GRANT OPTION;
GRANT ALL ON TABLE extensions.pg_stat_statements TO dashboard_user;


--
-- Name: TABLE pg_stat_statements_info; Type: ACL; Schema: extensions; Owner: -
--

REVOKE ALL ON TABLE extensions.pg_stat_statements_info FROM postgres;
GRANT ALL ON TABLE extensions.pg_stat_statements_info TO postgres WITH GRANT OPTION;
GRANT ALL ON TABLE extensions.pg_stat_statements_info TO dashboard_user;


--
-- Name: TABLE audit_logs; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.audit_logs TO anon;
GRANT ALL ON TABLE public.audit_logs TO authenticated;
GRANT ALL ON TABLE public.audit_logs TO service_role;


--
-- Name: TABLE brands; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.brands TO anon;
GRANT ALL ON TABLE public.brands TO authenticated;
GRANT ALL ON TABLE public.brands TO service_role;


--
-- Name: TABLE carrier_status_mapping; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.carrier_status_mapping TO anon;
GRANT ALL ON TABLE public.carrier_status_mapping TO authenticated;
GRANT ALL ON TABLE public.carrier_status_mapping TO service_role;


--
-- Name: SEQUENCE carrier_status_mapping_id_seq; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON SEQUENCE public.carrier_status_mapping_id_seq TO anon;
GRANT ALL ON SEQUENCE public.carrier_status_mapping_id_seq TO authenticated;
GRANT ALL ON SEQUENCE public.carrier_status_mapping_id_seq TO service_role;


--
-- Name: TABLE cart_items; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.cart_items TO anon;
GRANT ALL ON TABLE public.cart_items TO authenticated;
GRANT ALL ON TABLE public.cart_items TO service_role;


--
-- Name: TABLE categories; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.categories TO anon;
GRANT ALL ON TABLE public.categories TO authenticated;
GRANT ALL ON TABLE public.categories TO service_role;


--
-- Name: TABLE coupon_categories; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.coupon_categories TO anon;
GRANT ALL ON TABLE public.coupon_categories TO authenticated;
GRANT ALL ON TABLE public.coupon_categories TO service_role;


--
-- Name: TABLE coupon_products; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.coupon_products TO anon;
GRANT ALL ON TABLE public.coupon_products TO authenticated;
GRANT ALL ON TABLE public.coupon_products TO service_role;


--
-- Name: TABLE coupon_segments; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.coupon_segments TO anon;
GRANT ALL ON TABLE public.coupon_segments TO authenticated;
GRANT ALL ON TABLE public.coupon_segments TO service_role;


--
-- Name: TABLE coupon_usages; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.coupon_usages TO anon;
GRANT ALL ON TABLE public.coupon_usages TO authenticated;
GRANT ALL ON TABLE public.coupon_usages TO service_role;


--
-- Name: TABLE coupons; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.coupons TO anon;
GRANT ALL ON TABLE public.coupons TO authenticated;
GRANT ALL ON TABLE public.coupons TO service_role;


--
-- Name: TABLE favorites; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.favorites TO anon;
GRANT ALL ON TABLE public.favorites TO authenticated;
GRANT ALL ON TABLE public.favorites TO service_role;


--
-- Name: TABLE flash_sale_items; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.flash_sale_items TO anon;
GRANT ALL ON TABLE public.flash_sale_items TO authenticated;
GRANT ALL ON TABLE public.flash_sale_items TO service_role;


--
-- Name: TABLE flash_sales; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.flash_sales TO anon;
GRANT ALL ON TABLE public.flash_sales TO authenticated;
GRANT ALL ON TABLE public.flash_sales TO service_role;


--
-- Name: TABLE inventory_logs; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.inventory_logs TO anon;
GRANT ALL ON TABLE public.inventory_logs TO authenticated;
GRANT ALL ON TABLE public.inventory_logs TO service_role;


--
-- Name: TABLE order_items; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.order_items TO anon;
GRANT ALL ON TABLE public.order_items TO authenticated;
GRANT ALL ON TABLE public.order_items TO service_role;


--
-- Name: TABLE orders; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.orders TO anon;
GRANT ALL ON TABLE public.orders TO authenticated;
GRANT ALL ON TABLE public.orders TO service_role;


--
-- Name: TABLE payments; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.payments TO anon;
GRANT ALL ON TABLE public.payments TO authenticated;
GRANT ALL ON TABLE public.payments TO service_role;


--
-- Name: TABLE permission_groups; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.permission_groups TO anon;
GRANT ALL ON TABLE public.permission_groups TO authenticated;
GRANT ALL ON TABLE public.permission_groups TO service_role;


--
-- Name: SEQUENCE permission_groups_id_seq; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON SEQUENCE public.permission_groups_id_seq TO anon;
GRANT ALL ON SEQUENCE public.permission_groups_id_seq TO authenticated;
GRANT ALL ON SEQUENCE public.permission_groups_id_seq TO service_role;


--
-- Name: TABLE permissions; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.permissions TO anon;
GRANT ALL ON TABLE public.permissions TO authenticated;
GRANT ALL ON TABLE public.permissions TO service_role;


--
-- Name: SEQUENCE permissions_id_seq; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON SEQUENCE public.permissions_id_seq TO anon;
GRANT ALL ON SEQUENCE public.permissions_id_seq TO authenticated;
GRANT ALL ON SEQUENCE public.permissions_id_seq TO service_role;


--
-- Name: TABLE product_analytics; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.product_analytics TO anon;
GRANT ALL ON TABLE public.product_analytics TO authenticated;
GRANT ALL ON TABLE public.product_analytics TO service_role;


--
-- Name: TABLE product_images; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.product_images TO anon;
GRANT ALL ON TABLE public.product_images TO authenticated;
GRANT ALL ON TABLE public.product_images TO service_role;


--
-- Name: TABLE product_reviews; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.product_reviews TO anon;
GRANT ALL ON TABLE public.product_reviews TO authenticated;
GRANT ALL ON TABLE public.product_reviews TO service_role;


--
-- Name: TABLE product_variants; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.product_variants TO anon;
GRANT ALL ON TABLE public.product_variants TO authenticated;
GRANT ALL ON TABLE public.product_variants TO service_role;


--
-- Name: TABLE products; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.products TO anon;
GRANT ALL ON TABLE public.products TO authenticated;
GRANT ALL ON TABLE public.products TO service_role;


--
-- Name: TABLE return_requests; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.return_requests TO anon;
GRANT ALL ON TABLE public.return_requests TO authenticated;
GRANT ALL ON TABLE public.return_requests TO service_role;


--
-- Name: TABLE role_permissions; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.role_permissions TO anon;
GRANT ALL ON TABLE public.role_permissions TO authenticated;
GRANT ALL ON TABLE public.role_permissions TO service_role;


--
-- Name: TABLE roles; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.roles TO anon;
GRANT ALL ON TABLE public.roles TO authenticated;
GRANT ALL ON TABLE public.roles TO service_role;


--
-- Name: SEQUENCE roles_id_seq; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON SEQUENCE public.roles_id_seq TO anon;
GRANT ALL ON SEQUENCE public.roles_id_seq TO authenticated;
GRANT ALL ON SEQUENCE public.roles_id_seq TO service_role;


--
-- Name: TABLE shipment_events; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.shipment_events TO anon;
GRANT ALL ON TABLE public.shipment_events TO authenticated;
GRANT ALL ON TABLE public.shipment_events TO service_role;


--
-- Name: TABLE shipments; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.shipments TO anon;
GRANT ALL ON TABLE public.shipments TO authenticated;
GRANT ALL ON TABLE public.shipments TO service_role;


--
-- Name: TABLE shipping_configs; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.shipping_configs TO anon;
GRANT ALL ON TABLE public.shipping_configs TO authenticated;
GRANT ALL ON TABLE public.shipping_configs TO service_role;


--
-- Name: TABLE shipping_providers; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.shipping_providers TO anon;
GRANT ALL ON TABLE public.shipping_providers TO authenticated;
GRANT ALL ON TABLE public.shipping_providers TO service_role;


--
-- Name: TABLE system_settings; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.system_settings TO anon;
GRANT ALL ON TABLE public.system_settings TO authenticated;
GRANT ALL ON TABLE public.system_settings TO service_role;


--
-- Name: TABLE tenants; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.tenants TO anon;
GRANT ALL ON TABLE public.tenants TO authenticated;
GRANT ALL ON TABLE public.tenants TO service_role;


--
-- Name: TABLE user_addresses; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.user_addresses TO anon;
GRANT ALL ON TABLE public.user_addresses TO authenticated;
GRANT ALL ON TABLE public.user_addresses TO service_role;


--
-- Name: TABLE user_permissions; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.user_permissions TO anon;
GRANT ALL ON TABLE public.user_permissions TO authenticated;
GRANT ALL ON TABLE public.user_permissions TO service_role;


--
-- Name: TABLE user_roles; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.user_roles TO anon;
GRANT ALL ON TABLE public.user_roles TO authenticated;
GRANT ALL ON TABLE public.user_roles TO service_role;


--
-- Name: TABLE users; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.users TO anon;
GRANT ALL ON TABLE public.users TO authenticated;
GRANT ALL ON TABLE public.users TO service_role;


--
-- Name: TABLE webhook_logs; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.webhook_logs TO anon;
GRANT ALL ON TABLE public.webhook_logs TO authenticated;
GRANT ALL ON TABLE public.webhook_logs TO service_role;


--
-- Name: TABLE messages; Type: ACL; Schema: realtime; Owner: -
--

GRANT ALL ON TABLE realtime.messages TO postgres;
GRANT ALL ON TABLE realtime.messages TO dashboard_user;
GRANT SELECT,INSERT,UPDATE ON TABLE realtime.messages TO anon;
GRANT SELECT,INSERT,UPDATE ON TABLE realtime.messages TO authenticated;
GRANT SELECT,INSERT,UPDATE ON TABLE realtime.messages TO service_role;


--
-- Name: TABLE schema_migrations; Type: ACL; Schema: realtime; Owner: -
--

GRANT ALL ON TABLE realtime.schema_migrations TO postgres;
GRANT ALL ON TABLE realtime.schema_migrations TO dashboard_user;
GRANT SELECT ON TABLE realtime.schema_migrations TO anon;
GRANT SELECT ON TABLE realtime.schema_migrations TO authenticated;
GRANT SELECT ON TABLE realtime.schema_migrations TO service_role;
GRANT ALL ON TABLE realtime.schema_migrations TO supabase_realtime_admin;


--
-- Name: TABLE subscription; Type: ACL; Schema: realtime; Owner: -
--

GRANT ALL ON TABLE realtime.subscription TO postgres;
GRANT ALL ON TABLE realtime.subscription TO dashboard_user;
GRANT SELECT ON TABLE realtime.subscription TO anon;
GRANT SELECT ON TABLE realtime.subscription TO authenticated;
GRANT SELECT ON TABLE realtime.subscription TO service_role;
GRANT ALL ON TABLE realtime.subscription TO supabase_realtime_admin;


--
-- Name: SEQUENCE subscription_id_seq; Type: ACL; Schema: realtime; Owner: -
--

GRANT ALL ON SEQUENCE realtime.subscription_id_seq TO postgres;
GRANT ALL ON SEQUENCE realtime.subscription_id_seq TO dashboard_user;
GRANT USAGE ON SEQUENCE realtime.subscription_id_seq TO anon;
GRANT USAGE ON SEQUENCE realtime.subscription_id_seq TO authenticated;
GRANT USAGE ON SEQUENCE realtime.subscription_id_seq TO service_role;
GRANT ALL ON SEQUENCE realtime.subscription_id_seq TO supabase_realtime_admin;


--
-- Name: TABLE buckets; Type: ACL; Schema: storage; Owner: -
--

REVOKE ALL ON TABLE storage.buckets FROM supabase_storage_admin;
GRANT ALL ON TABLE storage.buckets TO supabase_storage_admin WITH GRANT OPTION;
GRANT ALL ON TABLE storage.buckets TO service_role;
GRANT ALL ON TABLE storage.buckets TO authenticated;
GRANT ALL ON TABLE storage.buckets TO anon;
GRANT ALL ON TABLE storage.buckets TO postgres WITH GRANT OPTION;


--
-- Name: TABLE buckets_analytics; Type: ACL; Schema: storage; Owner: -
--

GRANT ALL ON TABLE storage.buckets_analytics TO service_role;
GRANT ALL ON TABLE storage.buckets_analytics TO authenticated;
GRANT ALL ON TABLE storage.buckets_analytics TO anon;


--
-- Name: TABLE buckets_vectors; Type: ACL; Schema: storage; Owner: -
--

GRANT SELECT ON TABLE storage.buckets_vectors TO service_role;
GRANT SELECT ON TABLE storage.buckets_vectors TO authenticated;
GRANT SELECT ON TABLE storage.buckets_vectors TO anon;


--
-- Name: TABLE objects; Type: ACL; Schema: storage; Owner: -
--

REVOKE ALL ON TABLE storage.objects FROM supabase_storage_admin;
GRANT ALL ON TABLE storage.objects TO supabase_storage_admin WITH GRANT OPTION;
GRANT ALL ON TABLE storage.objects TO service_role;
GRANT ALL ON TABLE storage.objects TO authenticated;
GRANT ALL ON TABLE storage.objects TO anon;
GRANT ALL ON TABLE storage.objects TO postgres WITH GRANT OPTION;


--
-- Name: TABLE s3_multipart_uploads; Type: ACL; Schema: storage; Owner: -
--

GRANT ALL ON TABLE storage.s3_multipart_uploads TO service_role;
GRANT SELECT ON TABLE storage.s3_multipart_uploads TO authenticated;
GRANT SELECT ON TABLE storage.s3_multipart_uploads TO anon;


--
-- Name: TABLE s3_multipart_uploads_parts; Type: ACL; Schema: storage; Owner: -
--

GRANT ALL ON TABLE storage.s3_multipart_uploads_parts TO service_role;
GRANT SELECT ON TABLE storage.s3_multipart_uploads_parts TO authenticated;
GRANT SELECT ON TABLE storage.s3_multipart_uploads_parts TO anon;


--
-- Name: TABLE vector_indexes; Type: ACL; Schema: storage; Owner: -
--

GRANT SELECT ON TABLE storage.vector_indexes TO service_role;
GRANT SELECT ON TABLE storage.vector_indexes TO authenticated;
GRANT SELECT ON TABLE storage.vector_indexes TO anon;


--
-- Name: TABLE secrets; Type: ACL; Schema: vault; Owner: -
--

GRANT SELECT,REFERENCES,DELETE,TRUNCATE ON TABLE vault.secrets TO postgres WITH GRANT OPTION;
GRANT SELECT,DELETE ON TABLE vault.secrets TO service_role;


--
-- Name: TABLE decrypted_secrets; Type: ACL; Schema: vault; Owner: -
--

GRANT SELECT,REFERENCES,DELETE,TRUNCATE ON TABLE vault.decrypted_secrets TO postgres WITH GRANT OPTION;
GRANT SELECT,DELETE ON TABLE vault.decrypted_secrets TO service_role;


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: auth; Owner: -
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_auth_admin IN SCHEMA auth GRANT ALL ON SEQUENCES TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_auth_admin IN SCHEMA auth GRANT ALL ON SEQUENCES TO dashboard_user;


--
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: auth; Owner: -
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_auth_admin IN SCHEMA auth GRANT ALL ON FUNCTIONS TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_auth_admin IN SCHEMA auth GRANT ALL ON FUNCTIONS TO dashboard_user;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: auth; Owner: -
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_auth_admin IN SCHEMA auth GRANT ALL ON TABLES TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_auth_admin IN SCHEMA auth GRANT ALL ON TABLES TO dashboard_user;


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: extensions; Owner: -
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA extensions GRANT ALL ON SEQUENCES TO postgres WITH GRANT OPTION;


--
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: extensions; Owner: -
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA extensions GRANT ALL ON FUNCTIONS TO postgres WITH GRANT OPTION;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: extensions; Owner: -
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA extensions GRANT ALL ON TABLES TO postgres WITH GRANT OPTION;


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: graphql; Owner: -
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql GRANT ALL ON SEQUENCES TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql GRANT ALL ON SEQUENCES TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql GRANT ALL ON SEQUENCES TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql GRANT ALL ON SEQUENCES TO service_role;


--
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: graphql; Owner: -
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql GRANT ALL ON FUNCTIONS TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql GRANT ALL ON FUNCTIONS TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql GRANT ALL ON FUNCTIONS TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql GRANT ALL ON FUNCTIONS TO service_role;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: graphql; Owner: -
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql GRANT ALL ON TABLES TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql GRANT ALL ON TABLES TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql GRANT ALL ON TABLES TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql GRANT ALL ON TABLES TO service_role;


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: graphql_public; Owner: -
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql_public GRANT ALL ON SEQUENCES TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql_public GRANT ALL ON SEQUENCES TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql_public GRANT ALL ON SEQUENCES TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql_public GRANT ALL ON SEQUENCES TO service_role;


--
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: graphql_public; Owner: -
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql_public GRANT ALL ON FUNCTIONS TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql_public GRANT ALL ON FUNCTIONS TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql_public GRANT ALL ON FUNCTIONS TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql_public GRANT ALL ON FUNCTIONS TO service_role;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: graphql_public; Owner: -
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql_public GRANT ALL ON TABLES TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql_public GRANT ALL ON TABLES TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql_public GRANT ALL ON TABLES TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql_public GRANT ALL ON TABLES TO service_role;


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: public; Owner: -
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON SEQUENCES TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON SEQUENCES TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON SEQUENCES TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON SEQUENCES TO service_role;


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: public; Owner: -
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON SEQUENCES TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON SEQUENCES TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON SEQUENCES TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON SEQUENCES TO service_role;


--
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: public; Owner: -
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON FUNCTIONS TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON FUNCTIONS TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON FUNCTIONS TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON FUNCTIONS TO service_role;


--
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: public; Owner: -
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON FUNCTIONS TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON FUNCTIONS TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON FUNCTIONS TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON FUNCTIONS TO service_role;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: public; Owner: -
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON TABLES TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON TABLES TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON TABLES TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON TABLES TO service_role;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: public; Owner: -
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON TABLES TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON TABLES TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON TABLES TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON TABLES TO service_role;


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: realtime; Owner: -
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA realtime GRANT ALL ON SEQUENCES TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA realtime GRANT ALL ON SEQUENCES TO dashboard_user;


--
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: realtime; Owner: -
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA realtime GRANT ALL ON FUNCTIONS TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA realtime GRANT ALL ON FUNCTIONS TO dashboard_user;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: realtime; Owner: -
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA realtime GRANT ALL ON TABLES TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA realtime GRANT ALL ON TABLES TO dashboard_user;


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: storage; Owner: -
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA storage GRANT ALL ON SEQUENCES TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA storage GRANT ALL ON SEQUENCES TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA storage GRANT ALL ON SEQUENCES TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA storage GRANT ALL ON SEQUENCES TO service_role;


--
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: storage; Owner: -
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA storage GRANT ALL ON FUNCTIONS TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA storage GRANT ALL ON FUNCTIONS TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA storage GRANT ALL ON FUNCTIONS TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA storage GRANT ALL ON FUNCTIONS TO service_role;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: storage; Owner: -
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA storage GRANT ALL ON TABLES TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA storage GRANT ALL ON TABLES TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA storage GRANT ALL ON TABLES TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA storage GRANT ALL ON TABLES TO service_role;


--
-- Name: ensure_rls; Type: EVENT TRIGGER; Schema: -; Owner: -
--

CREATE EVENT TRIGGER ensure_rls ON ddl_command_end
         WHEN TAG IN ('CREATE TABLE', 'CREATE TABLE AS', 'SELECT INTO')
   EXECUTE FUNCTION public.rls_auto_enable();


--
-- Name: issue_graphql_placeholder; Type: EVENT TRIGGER; Schema: -; Owner: -
--

CREATE EVENT TRIGGER issue_graphql_placeholder ON sql_drop
         WHEN TAG IN ('DROP EXTENSION')
   EXECUTE FUNCTION extensions.set_graphql_placeholder();


--
-- Name: issue_pg_cron_access; Type: EVENT TRIGGER; Schema: -; Owner: -
--

CREATE EVENT TRIGGER issue_pg_cron_access ON ddl_command_end
         WHEN TAG IN ('CREATE EXTENSION')
   EXECUTE FUNCTION extensions.grant_pg_cron_access();


--
-- Name: issue_pg_graphql_access; Type: EVENT TRIGGER; Schema: -; Owner: -
--

CREATE EVENT TRIGGER issue_pg_graphql_access ON ddl_command_end
         WHEN TAG IN ('CREATE FUNCTION')
   EXECUTE FUNCTION extensions.grant_pg_graphql_access();


--
-- Name: issue_pg_net_access; Type: EVENT TRIGGER; Schema: -; Owner: -
--

CREATE EVENT TRIGGER issue_pg_net_access ON ddl_command_end
         WHEN TAG IN ('CREATE EXTENSION')
   EXECUTE FUNCTION extensions.grant_pg_net_access();


--
-- Name: pgrst_ddl_watch; Type: EVENT TRIGGER; Schema: -; Owner: -
--

CREATE EVENT TRIGGER pgrst_ddl_watch ON ddl_command_end
   EXECUTE FUNCTION extensions.pgrst_ddl_watch();


--
-- Name: pgrst_drop_watch; Type: EVENT TRIGGER; Schema: -; Owner: -
--

CREATE EVENT TRIGGER pgrst_drop_watch ON sql_drop
   EXECUTE FUNCTION extensions.pgrst_drop_watch();


--
-- PostgreSQL database dump complete
--

\unrestrict bikEs4g4SUDgbsWxHfXss9PMg6pbYyXbsZozlZDy9xrDjDwBclPwS8fO87OvKOe


--
-- PostgreSQL database dump
--

-- Dumped from database version 9.0.5
-- Dumped by pg_dump version 9.0.5
-- Started on 2012-03-15 17:30:58

SET statement_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = off;
SET check_function_bodies = false;
SET client_min_messages = warning;
SET escape_string_warning = off;

SET search_path = public, pg_catalog;

--
-- TOC entry 3085 (class 0 OID 0)
-- Dependencies: 233
-- Name: auth_group_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

INSERT INTO public.auth_group(name) 
 SELECT 'EDIT_' || resources.NAME
   FROM (SELECT 'HERITAGE_RESOURCE.E18' AS NAME UNION ALL
         SELECT 'HERITAGE_RESOURCE_GROUP.E27' UNION ALL
         SELECT 'ACTIVITY.E7' UNION ALL
         SELECT 'HISTORICAL_EVENT.E5' UNION ALL
         SELECT 'ACTOR.E39' UNION ALL
         SELECT 'INFORMATION_RESOURCE.E73') resources
 WHERE NOT EXISTS (SELECT * FROM public.auth_group ag1 WHERE ag1.NAME = 'EDIT_' || resources.NAME);

INSERT INTO public.auth_group(name) 
 SELECT 'PUBLISH_' || resources.NAME
   FROM (SELECT 'HERITAGE_RESOURCE.E18' AS NAME UNION ALL
         SELECT 'HERITAGE_RESOURCE_GROUP.E27' UNION ALL
         SELECT 'ACTIVITY.E7' UNION ALL
         SELECT 'HISTORICAL_EVENT.E5' UNION ALL
         SELECT 'ACTOR.E39' UNION ALL
         SELECT 'INFORMATION_RESOURCE.E73') resources
 WHERE NOT EXISTS (SELECT * FROM public.auth_group ag1 WHERE ag1.NAME = 'PUBLISH_' || resources.NAME);

INSERT INTO public.auth_group(name) 
 SELECT 'RDM'
  WHERE NOT EXISTS (SELECT * FROM public.auth_group ag1 WHERE ag1.NAME = 'RDM');

INSERT INTO public.auth_group(name) 
 SELECT 'OWNERSHIP_SLOVENIA_IPCHS'
 WHERE NOT EXISTS (SELECT * FROM public.auth_group ag1 WHERE ag1.NAME = 'OWNERSHIP_SLOVENIA_IPCHS');


-- Completed on 2012-03-15 17:30:59

--
-- PostgreSQL database dump complete
--

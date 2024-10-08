--©2024, Ovais Quraishi
CREATE DATABASE zollama;

--
-- PostgreSQL database dump
--

-- Dumped from database version 15.8 (Debian 15.8-1.pgdg120+1)
-- Dumped by pg_dump version 15.8 (Debian 15.8-1.pgdg120+1)

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

--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner:
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner:
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: cpt_hcpcs_codes; Type: TABLE; Schema: public; Owner: zollama
--

CREATE TABLE public.cpt_hcpcs_codes (
    id integer NOT NULL,
    "timestamp" timestamp with time zone NOT NULL,
    sha256 text NOT NULL,
    codes_document jsonb NOT NULL
);


ALTER TABLE public.cpt_hcpcs_codes OWNER TO zollama;

--
-- Name: cpt_hcpcs_codes_id_seq1; Type: SEQUENCE; Schema: public; Owner: zollama
--

ALTER TABLE public.cpt_hcpcs_codes ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.cpt_hcpcs_codes_id_seq1
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: embeddings; Type: TABLE; Schema: public; Owner: zollama
--

CREATE TABLE public.embeddings (
    id integer NOT NULL,
    url character varying(1000),
    title character varying(1000),
    text character varying,
    title_vector public.vector(1536),
    content_vector public.vector(1536),
    vector_id integer
);


ALTER TABLE public.embeddings OWNER TO zollama;

--
-- Name: medicare_data; Type: TABLE; Schema: public; Owner: zollama
--

CREATE TABLE public.medicare_data (
    mac text,
    lnum text,
    state text,
    fsa text,
    counties text
);


ALTER TABLE public.medicare_data OWNER TO zollama;

--
-- Name: old_patient_codes; Type: TABLE; Schema: public; Owner: zollama
--

CREATE TABLE public.old_patient_codes (
    id integer,
    "timestamp" timestamp with time zone,
    patient_id text,
    patient_document_id text,
    codes_document jsonb
);


ALTER TABLE public.old_patient_codes OWNER TO zollama;

--
-- Name: patient_codes; Type: TABLE; Schema: public; Owner: zollama
--

CREATE TABLE public.patient_codes (
    id integer NOT NULL,
    "timestamp" timestamp with time zone NOT NULL,
    patient_id text NOT NULL,
    patient_document_id text NOT NULL,
    codes_document jsonb NOT NULL
);


ALTER TABLE public.patient_codes OWNER TO zollama;

--
-- Name: patient_codes_id_seq; Type: SEQUENCE; Schema: public; Owner: zollama
--

ALTER TABLE public.patient_codes ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.patient_codes_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: patient_documents; Type: TABLE; Schema: public; Owner: zollama
--

CREATE TABLE public.patient_documents (
    id integer NOT NULL,
    "timestamp" timestamp with time zone NOT NULL,
    patient_document_id text NOT NULL,
    patient_id text NOT NULL,
    patient_note_id text NOT NULL,
    analysis_document jsonb NOT NULL,
    patient_locality character varying
);


ALTER TABLE public.patient_documents OWNER TO zollama;

--
-- Name: patient_documents_id_seq; Type: SEQUENCE; Schema: public; Owner: zollama
--

ALTER TABLE public.patient_documents ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.patient_documents_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: patient_notes; Type: TABLE; Schema: public; Owner: zollama
--

CREATE TABLE public.patient_notes (
    id integer NOT NULL,
    "timestamp" timestamp with time zone NOT NULL,
    patient_note_id text NOT NULL,
    patient_id text NOT NULL,
    patient_note jsonb NOT NULL
);


ALTER TABLE public.patient_notes OWNER TO zollama;

--
-- Name: patient_notes_id_seq; Type: SEQUENCE; Schema: public; Owner: zollama
--

ALTER TABLE public.patient_notes ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.patient_notes_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: cpt_hcpcs_codes cpt_hcpcs_codes_pkey1; Type: CONSTRAINT; Schema: public; Owner: zollama
--

ALTER TABLE ONLY public.cpt_hcpcs_codes
    ADD CONSTRAINT cpt_hcpcs_codes_pkey1 PRIMARY KEY (id);


--
-- Name: cpt_hcpcs_codes cpt_hcpcs_codes_sha256_key; Type: CONSTRAINT; Schema: public; Owner: zollama
--

ALTER TABLE ONLY public.cpt_hcpcs_codes
    ADD CONSTRAINT cpt_hcpcs_codes_sha256_key UNIQUE (sha256);


--
-- Name: embeddings embeddings_pkey; Type: CONSTRAINT; Schema: public; Owner: zollama
--

ALTER TABLE ONLY public.embeddings
    ADD CONSTRAINT embeddings_pkey PRIMARY KEY (id);


--
-- Name: patient_codes patient_codes_pkey; Type: CONSTRAINT; Schema: public; Owner: zollama
--

ALTER TABLE ONLY public.patient_codes
    ADD CONSTRAINT patient_codes_pkey PRIMARY KEY (id);


--
-- Name: patient_documents patient_documents_patient_document_id_key; Type: CONSTRAINT; Schema: public; Owner: zollama
--

ALTER TABLE ONLY public.patient_documents
    ADD CONSTRAINT patient_documents_patient_document_id_key UNIQUE (patient_document_id);


--
-- Name: patient_documents patient_documents_pkey; Type: CONSTRAINT; Schema: public; Owner: zollama
--

ALTER TABLE ONLY public.patient_documents
    ADD CONSTRAINT patient_documents_pkey PRIMARY KEY (id);


--
-- Name: patient_notes patient_notes_patient_note_id_key; Type: CONSTRAINT; Schema: public; Owner: zollama
--

ALTER TABLE ONLY public.patient_notes
    ADD CONSTRAINT patient_notes_patient_note_id_key UNIQUE (patient_note_id);


--
-- Name: patient_notes patient_notes_pkey; Type: CONSTRAINT; Schema: public; Owner: zollama
--

ALTER TABLE ONLY public.patient_notes
    ADD CONSTRAINT patient_notes_pkey PRIMARY KEY (id);


--
-- Name: analysis_document_gin_index; Type: INDEX; Schema: public; Owner: zollama
--

CREATE INDEX analysis_document_gin_index ON public.patient_documents USING gin (analysis_document jsonb_path_ops);


--
-- Name: idx_codes_document_gin; Type: INDEX; Schema: public; Owner: zollama
--

CREATE INDEX idx_codes_document_gin ON public.patient_codes USING gin (codes_document);


--
-- Name: idx_cpt_codes_sha256; Type: INDEX; Schema: public; Owner: zollama
--

CREATE INDEX idx_cpt_codes_sha256 ON public.cpt_hcpcs_codes USING btree (sha256);


--
-- Name: idx_mac; Type: INDEX; Schema: public; Owner: zollama
--

CREATE INDEX idx_mac ON public.medicare_data USING btree (mac);


--
-- Name: idx_patient_document_id; Type: INDEX; Schema: public; Owner: zollama
--

CREATE INDEX idx_patient_document_id ON public.patient_codes USING btree (patient_document_id);


--
-- Name: idx_patient_id; Type: INDEX; Schema: public; Owner: zollama
--

CREATE INDEX idx_patient_id ON public.patient_codes USING btree (patient_id);


--
-- Name: idx_timestamp; Type: INDEX; Schema: public; Owner: zollama
--

CREATE INDEX idx_timestamp ON public.patient_codes USING btree ("timestamp");


--
-- Name: patient_document_id_index; Type: INDEX; Schema: public; Owner: zollama
--

CREATE INDEX patient_document_id_index ON public.patient_documents USING btree (patient_document_id);


--
-- Name: patient_id_index; Type: INDEX; Schema: public; Owner: zollama
--

CREATE INDEX patient_id_index ON public.patient_notes USING btree (patient_id);


--
-- Name: patient_note_gin_index; Type: INDEX; Schema: public; Owner: zollama
--

CREATE INDEX patient_note_gin_index ON public.patient_notes USING gin (patient_note jsonb_path_ops);


--
-- Name: patient_note_id_index; Type: INDEX; Schema: public; Owner: zollama
--

CREATE INDEX patient_note_id_index ON public.patient_notes USING btree (patient_note_id);


--
-- Name: timestamp_index; Type: INDEX; Schema: public; Owner: zollama
--

CREATE INDEX timestamp_index ON public.patient_notes USING btree ("timestamp");


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: pg_database_owner
--

GRANT CREATE ON SCHEMA public TO zollama;


--
-- Name: TABLE cpt_hcpcs_codes; Type: ACL; Schema: public; Owner: zollama
--

GRANT ALL ON TABLE public.cpt_hcpcs_codes TO zollama;


--
-- Name: SEQUENCE cpt_hcpcs_codes_id_seq1; Type: ACL; Schema: public; Owner: zollama
--

GRANT SELECT,USAGE ON SEQUENCE public.cpt_hcpcs_codes_id_seq1 TO zollama;


--
-- Name: TABLE embeddings; Type: ACL; Schema: public; Owner: zollama
--

GRANT ALL ON TABLE public.embeddings TO zollama;


--
-- Name: TABLE medicare_data; Type: ACL; Schema: public; Owner: zollama
--

GRANT ALL ON TABLE public.medicare_data TO zollama;


--
-- Name: TABLE old_patient_codes; Type: ACL; Schema: public; Owner: zollama
--

GRANT ALL ON TABLE public.old_patient_codes TO zollama;


--
-- Name: TABLE patient_codes; Type: ACL; Schema: public; Owner: zollama
--

GRANT ALL ON TABLE public.patient_codes TO zollama;


--
-- Name: SEQUENCE patient_codes_id_seq; Type: ACL; Schema: public; Owner: zollama
--

GRANT SELECT,USAGE ON SEQUENCE public.patient_codes_id_seq TO zollama;


--
-- Name: TABLE patient_documents; Type: ACL; Schema: public; Owner: zollama
--

GRANT ALL ON TABLE public.patient_documents TO zollama;


--
-- Name: SEQUENCE patient_documents_id_seq; Type: ACL; Schema: public; Owner: zollama
--

GRANT SELECT,USAGE ON SEQUENCE public.patient_documents_id_seq TO zollama;


--
-- Name: TABLE patient_notes; Type: ACL; Schema: public; Owner: zollama
--

GRANT ALL ON TABLE public.patient_notes TO zollama;


--
-- Name: SEQUENCE patient_notes_id_seq; Type: ACL; Schema: public; Owner: zollama
--

GRANT SELECT,USAGE ON SEQUENCE public.patient_notes_id_seq TO zollama;


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: public; Owner: zollama
--

ALTER DEFAULT PRIVILEGES FOR ROLE zollama IN SCHEMA public GRANT SELECT,USAGE ON SEQUENCES  TO zollama;


--
-- PostgreSQL database dump complete
--

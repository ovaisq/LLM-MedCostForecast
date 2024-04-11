--©2024, Ovais Quraishi
CREATE DATABASE zollama;

CREATE EXTENSION IF NOT EXISTS pgcrypto;
DO $$
DECLARE
    generated_password TEXT;
BEGIN
    -- Generate the password and store it in the variable
    generated_password := encode(gen_random_bytes(20), 'base64');

    -- Check if the user already exists
    IF NOT EXISTS (SELECT 1 FROM pg_user WHERE usename = 'zollama') THEN
        -- Output the generated password
        RAISE NOTICE 'Generated password: %', generated_password;

        -- Create the user using the generated password
        EXECUTE format('CREATE USER zollama WITH PASSWORD %L', generated_password);
    ELSE
        RAISE NOTICE 'User "zollama" already exists. Skipping creation.';
    END IF;
END $$;

GRANT ALL PRIVILEGES ON DATABASE zollama TO zollama;
GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA public TO zollama;

CREATE EXTENSION vector;

CREATE TABLE cpt_hcpcs_codes (
	id int4 GENERATED BY DEFAULT AS IDENTITY( INCREMENT BY 1 MINVALUE 1 MAXVALUE 2147483647 START 1 CACHE 1 NO CYCLE) NOT NULL,
	"timestamp" timestamptz NOT NULL,
	sha256 text NOT NULL,
	codes_document jsonb NOT NULL,
	CONSTRAINT cpt_hcpcs_codes_pkey1 PRIMARY KEY (id),
	CONSTRAINT cpt_hcpcs_codes_sha256_key UNIQUE (sha256)
);
CREATE INDEX idx_cpt_codes_sha256 ON cpt_hcpcs_codes (sha256);
ALTER TABLE cpt_hcpcs_codes OWNER TO zollama;
GRANT ALL ON TABLE cpt_hcpcs_codes TO zollama;

CREATE TABLE embeddings (
	id int4 NOT NULL,
	url varchar(1000) NULL,
	title varchar(1000) NULL,
	"text" varchar NULL,
	title_vector vector NULL,
	content_vector vector NULL,
	vector_id int4 NULL,
	CONSTRAINT embeddings_pkey PRIMARY KEY (id)
);

ALTER TABLE embeddings OWNER TO zollama;
GRANT ALL ON TABLE embeddings TO zollama;

CREATE TABLE medicare_data (
	mac text NULL,
	lnum text NULL,
	state text NULL,
	fsa text NULL,
	counties text NULL
);
CREATE INDEX idx_mac ON medicare_data USING btree (mac);

ALTER TABLE medicare_data OWNER TO zollama;
GRANT ALL ON TABLE medicare_data TO zollama;

CREATE TABLE patient_codes (
	id int4 GENERATED BY DEFAULT AS IDENTITY( INCREMENT BY 1 MINVALUE 1 MAXVALUE 2147483647 START 1 CACHE 1 NO CYCLE) NOT NULL,
	"timestamp" timestamptz NOT NULL,
	patient_id text NOT NULL,
	patient_document_id text NOT NULL,
	codes_document jsonb NOT NULL,
	CONSTRAINT patient_codes_pkey PRIMARY KEY (id)
);
CREATE INDEX idx_codes_document_gin ON patient_codes USING gin (codes_document);
CREATE INDEX idx_patient_document_id ON patient_codes USING btree (patient_document_id);
CREATE INDEX idx_patient_id ON patient_codes USING btree (patient_id);
CREATE INDEX idx_timestamp ON patient_codes USING btree ("timestamp");

ALTER TABLE patient_codes OWNER TO zollama;
GRANT ALL ON TABLE patient_codes TO zollama;

CREATE TABLE patient_documents (
	id int4 GENERATED BY DEFAULT AS IDENTITY( INCREMENT BY 1 MINVALUE 1 MAXVALUE 2147483647 START 1 CACHE 1 NO CYCLE) NOT NULL,
	"timestamp" timestamptz NOT NULL,
	patient_document_id text NOT NULL,
	patient_id text NOT NULL,
	patient_note_id text NOT NULL,
	analysis_document jsonb NOT NULL,
	patient_locality varchar NULL,
	CONSTRAINT patient_documents_patient_document_id_key UNIQUE (patient_document_id),
	CONSTRAINT patient_documents_pkey PRIMARY KEY (id)
);
CREATE INDEX analysis_document_gin_index ON patient_documents USING gin (analysis_document jsonb_path_ops);
CREATE INDEX patient_document_id_index ON patient_documents USING btree (patient_document_id);

ALTER TABLE patient_documents OWNER TO zollama;
GRANT ALL ON TABLE patient_documents TO zollama;

CREATE TABLE patient_notes (
	id int4 GENERATED BY DEFAULT AS IDENTITY( INCREMENT BY 1 MINVALUE 1 MAXVALUE 2147483647 START 1 CACHE 1 NO CYCLE) NOT NULL,
	"timestamp" timestamptz NOT NULL,
	patient_note_id text NOT NULL,
	patient_id text NOT NULL,
	patient_note jsonb NOT NULL,
	CONSTRAINT patient_notes_patient_note_id_key UNIQUE (patient_note_id),
	CONSTRAINT patient_notes_pkey PRIMARY KEY (id)
);
CREATE INDEX patient_id_index ON patient_notes USING btree (patient_id);
CREATE INDEX patient_note_gin_index ON patient_notes USING gin (patient_note jsonb_path_ops);
CREATE INDEX patient_note_id_index ON patient_notes USING btree (patient_note_id);
CREATE INDEX timestamp_index ON patient_notes USING btree ("timestamp");


ALTER TABLE patient_notes OWNER TO zollama;
GRANT ALL ON TABLE patient_notes TO zollama;

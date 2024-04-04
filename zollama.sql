--©2024, Ovais Quraishi
CREATE DATABASE zollama;

--Create Tables
CREATE TABLE IF NOT EXISTS patient_notes (
    id integer PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
    timestamp timestamp with time zone NOT NULL,
    patient_note_id text UNIQUE NOT NULL,
    patient_id text NOT NULL,
    patient_note jsonb NOT NULL
);

CREATE TABLE IF NOT EXISTS patient_documents (
    id integer PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
    timestamp timestamp with time zone NOT NULL,
    patient_document_id text UNIQUE NOT NULL,
    patient_id text NOT NULL,
	patient_locality varchar,
    patient_note_id text NOT NULL,
    analysis_document jsonb NOT NULL
);

CREATE TABLE IF NOT EXISTS patient_codes (
    id integer PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
    timestamp timestamp with time zone NOT NULL,
    patient_id text NOT NULL,
    patient_document_id text NOT NULL,
    codes_document jsonb NOT NULL
);

CREATE TABLE IF NOT EXISTS cpt_hcpcs_codes (
    id integer PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
    timestamp timestamp with time zone NOT NULL,
    sha256 text UNIQUE NOT NULL,
    codes_document jsonb NOT NULL
);

CREATE TABLE IF NOT EXISTS medicare_data (
    mac text,
    lnum text,
    state text,
    fsa text,
    counties text 
);

--Create Indexes
--Medicare Data
CREATE INDEX idx_mac ON medicare_data (mac);

--CPT HCPCS Codes
CREATE INDEX idx_cpt_codes_timestamp ON cpt_hcpcs_codes (timestamp);
CREATE INDEX idx_cpt_codes_sha256 ON cpt_hcpcs_codes (sha256)
CREATE INDEX idx_cpt_codes_document_gin ON cpt_hcpcs_codes USING gin (codes_document);

--Patient Codes
CREATE INDEX idx_timestamp ON patient_codes (timestamp);
CREATE INDEX idx_patient_id ON patient_codes (patient_id);
CREATE INDEX idx_patient_document_id ON patient_codes (patient_document_id);
CREATE INDEX idx_codes_document_gin ON patient_codes USING gin (codes_document);

--Patient Notes
CREATE INDEX IF NOT EXISTS patient_note_id_index ON patient_notes (
    patient_note_id
);
CREATE INDEX IF NOT EXISTS patient_id_index ON patient_notes (patient_id);
CREATE INDEX IF NOT EXISTS timestamp_index ON patient_notes (timestamp);
CREATE INDEX IF NOT EXISTS patient_note_gin_index ON patient_notes USING gin (
    patient_note jsonb_path_ops
);
--Patient Documents
CREATE INDEX IF NOT EXISTS patient_document_id_index ON patient_documents (
    patient_document_id
);
CREATE INDEX IF NOT EXISTS patient_id_index ON patient_documents (patient_id);
CREATE INDEX IF NOT EXISTS patient_note_id_index ON patient_documents (
    patient_note_id
);
CREATE INDEX IF NOT EXISTS timestamp_index ON patient_documents (timestamp);
CREATE INDEX IF NOT EXISTS analysis_document_gin_index ON patient_documents USING gin (
    analysis_document jsonb_path_ops
);

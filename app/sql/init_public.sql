-- Creando la tabla Tenants
CREATE TABLE IF NOT EXISTS tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'esperando_agencia' CHECK (status IN ('activo','suspendido','prueba','esperando_agencia' )),
    expiry_date TIMESTAMPTZ NOT NULL, 
    phone_number TEXT UNIQUE NOT NULL, 
    email TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ,
    country TEXT,
    social_networks JSONB DEFAULT '{}'::jsonb,
    options JSONB DEFAULT '{}'::jsonb,
    features JSONB DEFAULT '{}'::jsonb,
    schema_name TEXT UNIQUE NOT NULL,
    ai_system_prompt TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb, 
    payment_plan TEXT NOT NULL DEFAULT 'basico' CHECK (payment_plan IN ('basico','profesional','enterprise')),
    partner_id INTEGER NOT NULL
);

-- INDICES DE RENDIMIENTO
CREATE INDEX IF NOT EXISTS idx_tenants_status ON tenants(status);
CREATE INDEX IF NOT EXISTS idx_tenants_features ON tenants USING GIN (features);
CREATE INDEX IF NOT EXISTS idx_tenants_options ON tenants USING GIN (options);
CREATE INDEX IF NOT EXISTS idx_tenants_metadata ON tenants USING GIN (metadata);

-- Creación de la Tabla Credentials
CREATE TABLE IF NOT EXISTS credentials (
    tenant_id UUID PRIMARY KEY,
    odoo_url TEXT UNIQUE,
    odoo_db TEXT UNIQUE,
    odoo_bot_user INTEGER,
    odoo_bot_api_key TEXT UNIQUE,
    tokens_platforms JSONB DEFAULT '{}'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT credentials_tenants 
        FOREIGN KEY (tenant_id) 
        REFERENCES tenants(id) 
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_credentials_tokens ON credentials USING GIN (tokens_platforms);
CREATE INDEX IF NOT EXISTS idx_credentials_metadata ON credentials USING GIN (metadata);

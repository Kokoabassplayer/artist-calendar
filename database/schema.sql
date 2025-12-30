-- =============================================
-- Artist Calendar - Supabase Database Schema
-- =============================================
-- Run this in Supabase SQL Editor to create tables
-- Supabase auto-creates auth.users for authentication

-- Enable UUID extension (Supabase has this by default)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================
-- ARTISTS TABLE
-- =============================================
CREATE TABLE artists (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    instagram_handle TEXT UNIQUE,
    facebook_url TEXT,
    contact_info TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast search
CREATE INDEX idx_artists_name ON artists USING GIN (to_tsvector('english', name));
CREATE INDEX idx_artists_instagram ON artists (instagram_handle);

-- =============================================
-- POSTERS TABLE
-- Stores extracted tour posters with versioning
-- =============================================
CREATE TABLE posters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    artist_id UUID REFERENCES artists(id) ON DELETE CASCADE,
    
    -- Image storage (Supabase Storage URL)
    image_url TEXT NOT NULL,
    
    -- Tour metadata
    tour_name TEXT,
    source_month CHAR(7) NOT NULL, -- YYYY-MM format
    
    -- Data source tracking
    source_type TEXT NOT NULL CHECK (source_type IN ('manual', 'instagram', 'facebook', 'website')),
    source_url TEXT, -- Original post URL if scraped
    source_post_id TEXT,
    source_profile TEXT,
    source_profile_url TEXT,
    source_posted_at TIMESTAMPTZ,
    source_caption TEXT,
    poster_confidence NUMERIC(4,3),
    uploaded_by UUID REFERENCES auth.users(id), -- NULL if scraped

    -- Image metadata
    image_hash TEXT,
    image_width INT,
    image_height INT,
    mime_type TEXT,
    language TEXT,

    -- Extraction tracking
    extraction_status TEXT DEFAULT 'pending'
        CHECK (extraction_status IN ('pending', 'processing', 'success', 'failed')),
    
    -- Versioning (for when posters get updated)
    version INT DEFAULT 1,
    is_latest BOOLEAN DEFAULT TRUE,
    
    -- Raw extraction data (for debugging)
    raw_json JSONB,
    
    -- Timestamps
    extracted_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast queries
CREATE INDEX idx_posters_artist ON posters (artist_id);
CREATE INDEX idx_posters_month ON posters (source_month);
CREATE INDEX idx_posters_latest ON posters (artist_id, source_month) WHERE is_latest = TRUE;
CREATE INDEX idx_posters_image_hash ON posters (image_hash);
CREATE INDEX idx_posters_source_url ON posters (source_url);
CREATE INDEX idx_posters_source_post_id ON posters (source_post_id);
CREATE INDEX idx_posters_extraction_status ON posters (extraction_status);

-- =============================================
-- LOCATIONS TABLE
-- Normalized venues/locations (optional, for dedupe)
-- =============================================
CREATE TABLE locations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT,
    address TEXT,
    city TEXT,
    province TEXT,
    country TEXT DEFAULT 'Thailand',
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    google_maps_url TEXT,
    google_place_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_locations_city ON locations (city);
CREATE INDEX idx_locations_province ON locations (province);
CREATE INDEX idx_locations_place_id ON locations (google_place_id);
CREATE INDEX idx_locations_lat_lng ON locations (latitude, longitude);

-- =============================================
-- EXTRACTIONS TABLE
-- Stores raw model outputs + structured JSON
-- =============================================
CREATE TABLE extractions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    poster_id UUID REFERENCES posters(id) ON DELETE CASCADE,
    model_provider TEXT NOT NULL,
    model_name TEXT NOT NULL,
    model_version TEXT,
    prompt_version TEXT,
    response_schema_version TEXT,
    status TEXT NOT NULL CHECK (status IN ('pending', 'success', 'failed')),
    confidence NUMERIC(4,3),
    raw_text TEXT,
    raw_json JSONB,
    structured_json JSONB,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_extractions_poster ON extractions (poster_id);
CREATE INDEX idx_extractions_status ON extractions (status);
CREATE INDEX idx_extractions_created ON extractions (created_at);

ALTER TABLE posters ADD COLUMN last_extraction_id UUID;
ALTER TABLE posters
    ADD CONSTRAINT fk_posters_last_extraction
    FOREIGN KEY (last_extraction_id) REFERENCES extractions(id) ON DELETE SET NULL;

-- =============================================
-- EVENTS TABLE
-- Individual tour dates extracted from posters
-- =============================================
CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    poster_id UUID REFERENCES posters(id) ON DELETE CASCADE,
    extraction_id UUID REFERENCES extractions(id) ON DELETE SET NULL,
    
    -- Event details
    date DATE NOT NULL,
    date_text TEXT,
    event_name TEXT,
    venue TEXT,
    location_id UUID REFERENCES locations(id) ON DELETE SET NULL,
    city TEXT,
    province TEXT,
    country TEXT DEFAULT 'Thailand',
    time TIME,
    time_text TEXT,
    timezone TEXT DEFAULT 'Asia/Bangkok',
    ticket_info TEXT,
    
    -- Status (for cancellations)
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'cancelled', 'postponed')),

    -- Review workflow
    review_status TEXT DEFAULT 'pending'
        CHECK (review_status IN ('pending', 'approved', 'rejected')),
    reviewed_by UUID REFERENCES auth.users(id),
    reviewed_at TIMESTAMPTZ,
    review_notes TEXT,

    -- Extraction metadata
    confidence NUMERIC(4,3),
    raw_text TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for user searches
CREATE INDEX idx_events_date ON events (date);
CREATE INDEX idx_events_city ON events (city);
CREATE INDEX idx_events_province ON events (province);
CREATE INDEX idx_events_status ON events (status) WHERE status = 'active';
CREATE INDEX idx_events_location_id ON events (location_id);
CREATE INDEX idx_events_review_status ON events (review_status);
CREATE INDEX idx_events_extraction_id ON events (extraction_id);

-- =============================================
-- USER PREFERENCES TABLE
-- Stores user's favorite artists and settings
-- =============================================
CREATE TABLE user_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE,
    
    -- Favorite artists (array of artist IDs)
    favorite_artists UUID[] DEFAULT '{}',
    
    -- Notification settings
    notify_new_events BOOLEAN DEFAULT TRUE,
    notify_cancellations BOOLEAN DEFAULT TRUE,
    
    -- Location preference (for filtering)
    preferred_provinces TEXT[] DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================
-- USER SAVED EVENTS TABLE
-- Events user wants to attend
-- =============================================
CREATE TABLE user_saved_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    event_id UUID REFERENCES events(id) ON DELETE CASCADE,
    
    -- User notes
    notes TEXT,
    
    -- Reminder
    remind_before_hours INT DEFAULT 24,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, event_id)
);

CREATE INDEX idx_saved_events_user ON user_saved_events (user_id);

-- =============================================
-- ROW LEVEL SECURITY (RLS)
-- Supabase best practice for data security
-- =============================================

-- Enable RLS on all tables
ALTER TABLE artists ENABLE ROW LEVEL SECURITY;
ALTER TABLE posters ENABLE ROW LEVEL SECURITY;
ALTER TABLE locations ENABLE ROW LEVEL SECURITY;
ALTER TABLE extractions ENABLE ROW LEVEL SECURITY;
ALTER TABLE events ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_saved_events ENABLE ROW LEVEL SECURITY;

-- Public read access for artists, posters, events
CREATE POLICY "Public read access" ON artists FOR SELECT USING (true);
CREATE POLICY "Public read access" ON posters FOR SELECT USING (true);
CREATE POLICY "Public read access" ON locations FOR SELECT USING (true);
CREATE POLICY "Public read access" ON events FOR SELECT USING (true);

-- Users can only access their own preferences
CREATE POLICY "Users own preferences" ON user_preferences
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users own saved events" ON user_saved_events
    FOR ALL USING (auth.uid() = user_id);

-- Extractions are service-role only by default (no public policy).

-- Admin can insert/update posters (you'll set this up in Supabase dashboard)
-- For now, authenticated users can upload
CREATE POLICY "Authenticated users can upload" ON posters
    FOR INSERT WITH CHECK (auth.role() = 'authenticated');

-- =============================================
-- USEFUL VIEWS
-- =============================================

-- View: Upcoming events with artist info
CREATE VIEW upcoming_events AS
SELECT 
    e.id,
    e.date,
    e.event_name,
    e.venue,
    e.city,
    e.province,
    e.country,
    e.time,
    e.ticket_info,
    e.status,
    a.name AS artist_name,
    a.instagram_handle,
    p.image_url AS poster_url,
    p.tour_name
FROM events e
JOIN posters p ON e.poster_id = p.id AND p.is_latest = TRUE
JOIN artists a ON p.artist_id = a.id
WHERE e.date >= CURRENT_DATE
  AND e.status = 'active'
ORDER BY e.date ASC;

-- View: Popular artists (by number of events)
CREATE VIEW popular_artists AS
SELECT 
    a.id,
    a.name,
    a.instagram_handle,
    COUNT(e.id) AS event_count
FROM artists a
JOIN posters p ON p.artist_id = a.id AND p.is_latest = TRUE
JOIN events e ON e.poster_id = p.id AND e.status = 'active' AND e.date >= CURRENT_DATE
GROUP BY a.id
ORDER BY event_count DESC;

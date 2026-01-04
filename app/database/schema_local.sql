PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS artists (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    instagram_handle TEXT UNIQUE,
    facebook_url TEXT,
    contact_info TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_artists_name ON artists (name);
CREATE INDEX IF NOT EXISTS idx_artists_instagram ON artists (instagram_handle);

CREATE TABLE IF NOT EXISTS posters (
    id TEXT PRIMARY KEY,
    artist_id TEXT NOT NULL,
    image_url TEXT NOT NULL,
    tour_name TEXT,
    source_month TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_url TEXT,
    source_post_id TEXT,
    source_profile TEXT,
    source_profile_url TEXT,
    source_posted_at TEXT,
    source_caption TEXT,
    poster_confidence REAL,
    image_hash TEXT,
    image_width INTEGER,
    image_height INTEGER,
    mime_type TEXT,
    language TEXT,
    extraction_status TEXT DEFAULT 'pending',
    version INTEGER DEFAULT 1,
    is_latest INTEGER DEFAULT 1,
    raw_json TEXT,
    extracted_at TEXT DEFAULT CURRENT_TIMESTAMP,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (artist_id) REFERENCES artists(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_posters_artist ON posters (artist_id);
CREATE INDEX IF NOT EXISTS idx_posters_month ON posters (source_month);
CREATE INDEX IF NOT EXISTS idx_posters_latest ON posters (artist_id, source_month, is_latest);
CREATE INDEX IF NOT EXISTS idx_posters_source_url ON posters (source_url);
CREATE INDEX IF NOT EXISTS idx_posters_source_post_id ON posters (source_post_id);
CREATE INDEX IF NOT EXISTS idx_posters_extraction_status ON posters (extraction_status);

CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    poster_id TEXT NOT NULL,
    date TEXT NOT NULL,
    date_text TEXT,
    event_name TEXT,
    venue TEXT,
    city TEXT,
    province TEXT,
    country TEXT DEFAULT 'Thailand',
    time TEXT,
    time_text TEXT,
    timezone TEXT DEFAULT 'Asia/Bangkok',
    ticket_info TEXT,
    status TEXT DEFAULT 'active',
    review_status TEXT DEFAULT 'pending',
    confidence REAL,
    raw_text TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (poster_id) REFERENCES posters(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_events_date ON events (date);
CREATE INDEX IF NOT EXISTS idx_events_city ON events (city);
CREATE INDEX IF NOT EXISTS idx_events_province ON events (province);
CREATE INDEX IF NOT EXISTS idx_events_status ON events (status);
CREATE INDEX IF NOT EXISTS idx_events_review_status ON events (review_status);

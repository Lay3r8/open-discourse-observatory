WITH documents AS (
  SELECT
    DATE AS gdelt_date,
    SourceCommonName AS source_common_name,
    DocumentIdentifier AS url,
    REGEXP_EXTRACT(Extras, r'<PAGE_TITLE>(.*?)</PAGE_TITLE>') AS title_raw,
    LOWER(REGEXP_EXTRACT(Extras, r'<PAGE_TITLE>(.*?)</PAGE_TITLE>')) AS title_lower,
    REGEXP_EXTRACT(TranslationInfo, r'srclc:(.*?);') AS source_language,
    V2Themes AS themes,
    V2Persons AS persons,
    V2Organizations AS organizations,
    V2Locations AS locations
  FROM `gdelt-bq.gdeltv2.gkg_partitioned`
  WHERE _PARTITIONTIME >= @start_ts
    AND _PARTITIONTIME < @end_ts
    AND Extras LIKE '%<PAGE_TITLE>%'
),
scored AS (
  SELECT
    *,
    CASE
      WHEN (source_language IS NULL OR source_language = 'eng')
        AND REGEXP_CONTAINS(title_lower, @english_pattern) THEN TRUE
      WHEN source_language = 'fra'
        AND REGEXP_CONTAINS(title_lower, @french_pattern) THEN TRUE
      WHEN source_language = 'nld'
        AND REGEXP_CONTAINS(title_lower, @dutch_pattern) THEN TRUE
      ELSE FALSE
    END AS is_candidate,
    CASE
      WHEN (source_language IS NULL OR source_language = 'eng')
        AND REGEXP_CONTAINS(title_lower, @english_pattern)
        THEN REGEXP_EXTRACT(title_lower, @english_pattern)
      WHEN source_language = 'fra'
        AND REGEXP_CONTAINS(title_lower, @french_pattern)
        THEN REGEXP_EXTRACT(title_lower, @french_pattern)
      WHEN source_language = 'nld'
        AND REGEXP_CONTAINS(title_lower, @dutch_pattern)
        THEN REGEXP_EXTRACT(title_lower, @dutch_pattern)
      ELSE NULL
    END AS matched_token
  FROM documents
),
sampled AS (
  SELECT
    *,
    CASE WHEN is_candidate THEN 'candidate' ELSE 'negative_control' END AS sample_kind
  FROM scored
  WHERE is_candidate
     OR (
       NOT is_candidate
       AND MOD(FARM_FINGERPRINT(COALESCE(url, '')), @negative_sample_modulus) = 0
     )
)
SELECT
  gdelt_date,
  source_common_name,
  source_language,
  title_raw,
  url,
  themes,
  persons,
  organizations,
  locations,
  sample_kind,
  matched_token
FROM sampled

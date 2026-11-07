# Graph Report - challengex  (2026-11-06)

## Corpus Check
- Large corpus: 111 files · ~913,846 words. Semantic extraction will be expensive (many Claude tokens). Consider running on a subfolder.

## Summary
- 1035 nodes · 2193 edges · 63 communities (45 shown, 18 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 110 edges (avg confidence: 0.92)
- Token cost: 273,692 input · 0 output

## Community Hubs (Navigation)
- Header Parsing & Accessibility
- AI Summary Templates
- Table Display Pipeline
- AI Summary Number Check
- AI Page Tests
- AI Change Claim Checks
- Household Group Crosstabs
- Title Recovery
- Raw Table Loading
- AI Summary Filtering
- AI Summary Retrieval & Evals
- Methodology Breaks & Forecast Link
- Old Report Extraction
- Gemini Prompt & Generation
- Overview KPIs & CSV
- Trends Copy Tests
- Metric Loader Tests
- Report Excerpt Extraction
- Preferred Value Selection
- PDF Table Re-read
- PDF Verification Parsing
- AI Summary File Storage
- AI Summaries Tab View
- Prose Paragraph Parsing
- Forecast Models & Backtest
- Forecast Model Tests
- Sentence Excerpt Matching
- PyMuPDF Paragraph Blocks
- Table Browser Tests
- Overview & Year Tests
- Django Entry Points
- Data Sources & Traps
- Security & Dependencies
- Admin Registrations
- AI Generate & Review Views
- Table Page Tests
- Demographics Load Tests
- Challenge Goals & Personas
- Summary Data Preparation
- AI Export & Filters
- Trend Forecast Tests
- Metric Source Mapping
- Accessibility Tests
- Quality Bar Criteria
- Verification & Rebuild Docs
- PDF Verify Command
- Gemini Call Tests
- Context File Tests
- Demo Script & Provenance
- Search-to-Section Matching
- AI Summaries List View
- Database Migrations
- Text Cleaning for Checks
- Rebuild DB Command
- Re-read Number Consistency
- App Config
- AI Roadmap Notes
- USPS Logo
- Yearly Summary Lookup

## God Nodes (most connected - your core abstractions)
1. `Observation` - 39 edges
2. `Table` - 34 edges
3. `AiPageTests` - 33 edges
4. `ValidateTests` - 30 edges
5. `RealDataTests` - 27 edges
6. `LoadMetricsTests` - 27 edges
7. `load_real_tables()` - 24 edges
8. `tidy()` - 24 edges
9. `validate_ai_summary()` - 23 edges
10. `MethodologyBreak` - 21 edges

## Surprising Connections (you probably didn't know these)
- `Summary staleness check per data version and input hash` --references--> `validate_ai_summary()`  [INFERRED]
  CLAUDE.md → dashboard/ai_summary.py
- `validate_ai_summary()` --implements--> `AI summary validation check (whose number, which year, which change, direction, breaks)`  [EXTRACTED]
  dashboard/ai_summary.py → CLAUDE.md
- `Provenance: every number traces to source_table, report year and page` --rationale_for--> `Observation`  [INFERRED]
  CLAUDE.md → dashboard/models.py
- `Household groups (age, income, education segments)` --references--> `Segment`  [EXTRACTED]
  CLAUDE.md → dashboard/models.py
- `Methodology breaks (NuStats to RCF, FY2025 redesign, MSA, age bands)` --implements--> `MethodologyBreak`  [INFERRED]
  CLAUDE.md → dashboard/models.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **rebuild_db load-and-verify flow** — dashboard_management_commands_rebuild_db, dashboard_management_commands_load_tables, dashboard_management_commands_load_metrics, dashboard_management_commands_verify_pdfs, dashboard_metric_sources, claude_tables_json, claude_tables_2000_2015_json [EXTRACTED 1.00]
- **Known data-quality traps for trend lines** — claude_fy2021_ocr_problem, claude_correspondence_reclassification, claude_column_position_trap, claude_unit_changes, claude_methodology_breaks, claude_restatements [EXTRACTED 1.00]
- **AI summary generation and safeguards** — dashboard_ai_summary, dashboard_ai_summary_validate_ai_summary, dashboard_ai_summary_save_summary, dashboard_ai_views, claude_ai_staleness, claude_genai_guardrails [INFERRED 0.85]
- **Copy with sources into a report (OIG report prep)** — dashboard_templates_dashboard_ai_summaries_copy_script, dashboard_templates_dashboard_trends_copy_script, dashboard_templates_dashboard__ai_item_copy_source, dashboard_templates_dashboard_ai_summary_detail [INFERRED 0.85]
- **Generative AI safeguards in the summary UI** — dashboard_templates_dashboard__ai_summary_number_check, dashboard_templates_dashboard__ai_summary_review_status, dashboard_templates_dashboard__ai_summary_autoescape_rule, dashboard_templates_dashboard__ai_generate_form_fixed_list_criteria, dashboard_templates_dashboard_ai_summary_detail_provenance_metadata, dashboard_templates_dashboard_ai_summaries_hidden_failed [INFERRED 0.85]
- **Full pages sharing _head and _nav chrome** — dashboard_templates_dashboard_ai_summaries, dashboard_templates_dashboard_ai_summary_detail, dashboard_templates_dashboard_overview, dashboard_templates_dashboard_table_detail, dashboard_templates_dashboard_table_list, dashboard_templates_dashboard_trends, dashboard_templates_dashboard_year, dashboard_templates_dashboard__head, dashboard_templates_dashboard__nav [EXTRACTED 1.00]

## Communities (63 total, 18 thin omitted)

### Community 0 - "Header Parsing & Accessibility"
Cohesion: 0.07
Nodes (9): year_header(), LoadTwoFilesTests, cited_old_tables(), cited_old_tables_path(), load_real_tables(), ConversionTests, MappingTests, RebuildDbTests (+1 more)

### Community 1 - "AI Summary Templates"
Cohesion: 0.06
Nodes (50): _ai_generate_form.html (Create a summary form), URL ai-generate (POST, CSRF token), Kind-dependent year field toggle script, Hourly live-generation limit (live_left, live_unavailable), _ai_item.html (folded summary row), Hidden copy-source pre with sources, _ai_summary.html (stored AI summary), Automated number check of summaries (+42 more)

### Community 2 - "Table Display Pipeline"
Cohesion: 0.06
Nodes (14): chapter_of(), display_table(), join_wrapped_labels(), _load_context(), rebuilt_display(), review_reasons(), section_of(), table_context() (+6 more)

### Community 3 - "AI Summary Number Check"
Cohesion: 0.09
Nodes (9): Summary staleness check per data version and input hash, _group_tokens(), _named_breaks(), _note_years(), _scope(), _text_numbers(), validate_ai_summary(), summary() (+1 more)

### Community 4 - "AI Page Tests"
Cohesion: 0.14
Nodes (4): AiPageTests, wrong(), record(), yearly()

### Community 5 - "AI Change Claim Checks"
Cohesion: 0.10
Nodes (15): _before_window(), _check_change(), _check_scoped(), _check_unscoped(), _clause(), _close(), _direction(), _is_change() (+7 more)

### Community 6 - "Household Group Crosstabs"
Cohesion: 0.11
Nodes (15): Household groups (age, income, education segments), check_heading(), crosstab_values(), income_band(), change_columns(), crosstab_items(), find_row(), norm() (+7 more)

### Community 7 - "Title Recovery"
Cohesion: 0.11
Nodes (14): table_titles.json (corrected titles and numbers), Command, TitleTests, assign_page(), assign_report(), caption_words(), captions(), fix_line() (+6 more)

### Community 8 - "Raw Table Loading"
Cohesion: 0.11
Nodes (12): cells(), Command, prune_stale(), read_items(), stale_tables(), unique_columns(), Migration, Table (+4 more)

### Community 9 - "AI Summary Filtering"
Cohesion: 0.14
Nodes (19): category_of(), check_batch(), covers_year(), entry_order(), is_year(), matches(), metric_name(), plain_text() (+11 more)

### Community 10 - "AI Summary Retrieval & Evals"
Cohesion: 0.16
Nodes (3): collect_section(), get_summary(), RealDataTests

### Community 11 - "Methodology Breaks & Forecast Link"
Cohesion: 0.11
Nodes (17): Methodology breaks (NuStats to RCF, FY2025 redesign, MSA, age bands), tables_2000_2015.json (1,933 tables FY2003-FY2015), section_for_trend(), forecast(), MethodologyBreak, Meta, csv_response(), observation_row() (+9 more)

### Community 12 - "Old Report Extraction"
Cohesion: 0.11
Nodes (10): caption_title(), clean_grid(), Command, is_contents_page(), number_tokens(), split_header(), text_check(), text_lines() (+2 more)

### Community 13 - "Gemini Prompt & Generation"
Cohesion: 0.11
Nodes (10): build_prompt(), current_check(), _data_version(), generate_ai_summary(), input_hash(), main(), make_summary(), _record_hash() (+2 more)

### Community 14 - "Overview KPIs & CSV"
Cohesion: 0.15
Nodes (12): decimals(), fmt(), fmt_change(), kpi_card(), market_mix(), overview(), preferred(), safe_cell() (+4 more)

### Community 17 - "Report Excerpt Extraction"
Cohesion: 0.15
Nodes (6): table_context.json (excerpts, units, PDF re-reads), Command, implausible(), leaks(), score(), ReReadTests

### Community 18 - "Preferred Value Selection"
Cohesion: 0.14
Nodes (9): Command, mark_preferred(), Metric, Meta, Observation, Meta, Segment, Meta (+1 more)

### Community 19 - "PDF Table Re-read"
Cohesion: 0.14
Nodes (8): caption_units(), _cells(), find_caption(), _norm(), rebuild(), _spans(), _value_columns(), wrapped_labels()

### Community 20 - "PDF Verification Parsing"
Cohesion: 0.16
Nodes (6): header_line(), label_rows(), norm(), page_series(), year_header(), PdfTextTests

### Community 21 - "AI Summary File Storage"
Cohesion: 0.15
Nodes (7): _load_file(), _path(), save_summary(), set_reviewed(), shown(), stored_entries(), _write_file()

### Community 22 - "AI Summaries Tab View"
Cohesion: 0.14
Nodes (7): _counters(), _hidden_reason(), _left(), _limits(), _preview(), _status(), _take_one()

### Community 23 - "Prose Paragraph Parsing"
Cohesion: 0.19
Nodes (7): continues(), is_caption(), _is_prose(), join_lines(), norm(), paragraphs_from_lines(), stitch()

### Community 24 - "Forecast Models & Backtest"
Cohesion: 0.15
Nodes (6): backtest(), errors(), fit_window(), holt(), holt_params(), _holt_run()

### Community 25 - "Forecast Model Tests"
Cohesion: 0.12
Nodes (3): ForecastTests, ModelTests, WindowTests

### Community 26 - "Sentence Excerpt Matching"
Cohesion: 0.22
Nodes (4): excerpts(), mentions(), sentences(), SentenceTests

### Community 27 - "PyMuPDF Paragraph Blocks"
Cohesion: 0.24
Nodes (4): _letter_spaced(), paragraphs_from_blocks(), _wordy(), ParagraphTests

### Community 31 - "Data Sources & Traps"
Cohesion: 0.20
Nodes (11): Appendix A trend tables (A8-x / A-x) as primary trend source, Correspondence/transactions split reclassified, FY2021 OCR chapter tables are wrong, Required capabilities (15+ years, by year/product/demographics, summaries, forecasting), Restatements: prefer most recent non-OCR report (mark_preferred), tables.json (1,095 tables FY2016-FY2025), Projection track record: drift wins with 0.24x naive error, Headline figures (637.3 pieces/household FY2025, bills by mail 14%, packages 41.5) (+3 more)

### Community 32 - "Security & Dependencies"
Cohesion: 0.22
Nodes (10): Create a new summary (live Gemini call with CSRF, rate limits, timeout), requirements.txt (pinned runtime dependencies), asgiref==3.12.1, requirements-dev.txt (developer tools), pip-audit==2.10.1, pymupdf==1.28.2, Django==6.1.2, pypdf==6.21.4 (+2 more)

### Community 33 - "Admin Registrations"
Cohesion: 0.29
Nodes (9): MethodologyBreakAdmin, MetricAdmin, ObservationAdmin, RowAdmin, RowInline, SegmentAdmin, TableAdmin, Row (+1 more)

### Community 34 - "AI Generate & Review Views"
Cohesion: 0.22
Nodes (5): ai_generate(), ai_review(), _dotenv(), gemini_key(), live_unavailable()

### Community 36 - "Demographics Load Tests"
Cohesion: 0.24
Nodes (3): LoadDemographicsTests, years(), line()

### Community 37 - "Challenge Goals & Personas"
Cohesion: 0.20
Nodes (8): Augmented analytics data product (ETL, dimensional model, BI, forecasting + LLM), ChallengeX USPS Household Mail Dashboard (Group 2), Household Diary Study / Household Mail Survey (HDS/HMS), How Americans Use Mail (OIG report, 50% prep-time goal), OIG analyst persona / user stories, Postal Insights: Analyzing US Mail Usage Through an Interactive Dashboard, USPS Office of Inspector General (OIG), python-dotenv==1.2.4

### Community 38 - "Summary Data Preparation"
Cohesion: 0.24
Nodes (5): _change(), _forecast_entry(), prepare_summary_data(), _round(), _series_entry()

### Community 39 - "AI Export & Filters"
Cohesion: 0.22
Nodes (6): ai_export(), _choice(), _filters(), fiscal_years(), year_param(), year_pick()

### Community 41 - "Metric Source Mapping"
Cohesion: 0.25
Nodes (4): Unit changes (millions, billions, per household per week/year), crosstabs(), RowMap, segment_rows()

### Community 43 - "Quality Bar Criteria"
Cohesion: 0.25
Nodes (4): AI summary validation check (whose number, which year, which change, direction, breaks), Ask the data box (optional, untrusted input), Naive, drift, linear and Holt models chosen by rolling-origin backtest, WCAG 2.1 AA / Section 508 accessibility

### Community 44 - "Verification & Rebuild Docs"
Cohesion: 0.25
Nodes (7): docs/ source PDFs (git-ignored), rebuild_db pipeline (migrate, load_tables, load_metrics, verify_pdfs), Cross-report checks (A8-3, A8-6 vs A-6, A8-12, FY2025 A-3/A-6/A-11), Data verification: loaded metrics vs. the source reports, Every file in docs/ checked, Education vs. age table margins check (254 of 260 identical), What could not be checked (FY2024 per-household series, FY2000/2001 bills)

### Community 45 - "PDF Verify Command"
Cohesion: 0.36
Nodes (3): to_num(), Command, set_note()

### Community 48 - "Demo Script & Provenance"
Cohesion: 0.29
Nodes (5): Demo script: Postal Insights dashboard (about 7 minutes), Likely questions (Where's the AI, accuracy, restatements, gaps), Before the demo checklist (rebuild_db 1592 match, tests, PDFs, CDN internet), Story: every number one click from its source page, with honest projections, If something goes wrong (CDN, missing docs/, empty DB)

### Community 49 - "Search-to-Section Matching"
Cohesion: 0.33
Nodes (4): search_terms(), section_for_words(), year_in_words(), _suggestion()

### Community 50 - "AI Summaries List View"
Cohesion: 0.29
Nodes (4): year_spans(), ai_summaries(), _status_line(), _subjects()

### Community 51 - "Database Migrations"
Cohesion: 0.29
Nodes (3): Migration, Migration, Migration

### Community 52 - "Text Cleaning for Checks"
Cohesion: 0.33
Nodes (4): _mark_groups(), _strip_stock(), replace(), clean()

### Community 57 - "AI Roadmap Notes"
Cohesion: 0.67
Nodes (3): AI summaries with Google Gemini (prompt summary-v2), Insight model / generate_insights original design (Claude API), Next steps (priority order)

### Community 58 - "USPS Logo"
Cohesion: 0.67
Nodes (3): USPS eagle logo (mobile SVG), Compact eagle-head mark in slanted parallelogram with registered-trademark symbol, Brand palette (#004B87, #243E8F, white)

## Knowledge Gaps
- **36 isolated node(s):** `Household Diary Study / Household Mail Survey (HDS/HMS)`, `WCAG 2.1 AA / Section 508 accessibility`, `Unit changes (millions, billions, per household per week/year)`, `Summary staleness check per data version and input hash`, `Insight model / generate_insights original design (Claude API)` (+31 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 358 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **18 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Observation` connect `Preferred Value Selection` to `Header Parsing & Accessibility`, `Admin Registrations`, `Demographics Load Tests`, `AI Change Claim Checks`, `Household Group Crosstabs`, `AI Export & Filters`, `Raw Table Loading`, `AI Summary Retrieval & Evals`, `Methodology Breaks & Forecast Link`, `Gemini Prompt & Generation`, `PDF Verify Command`, `Overview KPIs & CSV`, `Demo Script & Provenance`, `Trends Copy Tests`, `Metric Loader Tests`, `Rebuild DB Command`, `Overview & Year Tests`?**
  _High betweenness centrality (0.134) - this node is a cross-community bridge._
- **Are the 19 inferred relationships involving `Observation` (e.g. with `Provenance: every number traces to source_table, report year and page` and `collect_section()`) actually correct?**
  _`Observation` has 19 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Household Diary Study / Household Mail Survey (HDS/HMS)`, `WCAG 2.1 AA / Section 508 accessibility`, `Unit changes (millions, billions, per household per week/year)` to the rest of the system?**
  _36 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Header Parsing & Accessibility` be split into smaller, more focused modules?**
  _Cohesion score 0.06810035842293907 - nodes in this community are weakly interconnected._
- **Why does `Table` connect `Raw Table Loading` to `Header Parsing & Accessibility`, `Admin Registrations`, `Table Page Tests`, `Household Group Crosstabs`, `Accessibility Tests`, `PDF Verify Command`, `Overview KPIs & CSV`, `Metric Loader Tests`, `Report Excerpt Extraction`, `Preferred Value Selection`, `Rebuild DB Command`, `Table Browser Tests`?**
  _High betweenness centrality (0.073) - this node is a cross-community bridge._
- **Are the 16 inferred relationships involving `Table` (e.g. with `Command` and `Command`) actually correct?**
  _`Table` has 16 INFERRED edges - model-reasoned connections that need verification._
- **Should `AI Summary Templates` be split into smaller, more focused modules?**
  _Cohesion score 0.05805515239477504 - nodes in this community are weakly interconnected._
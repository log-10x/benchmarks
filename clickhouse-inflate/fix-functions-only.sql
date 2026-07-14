-- The fix, and ONLY the fix: the two core inflate functions, replaced.
--
-- Applied on its own this is deliberately NOT enough. ClickHouse expands a SQL
-- function's body into a view's stored AST at CREATE VIEW time, so tenx.events
-- and tenx.events_native keep running the body they inlined at creation and
-- keep blowing up. run.sh applies this file, then greps SHOW CREATE VIEW to
-- show the old body still sitting inside the view, before applying
-- install-fixed.sql (which recreates the views).
--
-- Copied verbatim from section 6 of install-fixed.sql.

CREATE OR REPLACE FUNCTION tenx_inflate_core AS (literals, slots, values) ->
    arrayStringConcat(
      arrayMap((lit, slot, val) -> concat(lit, tenx_substitute_slot(val, slot)),
        literals,
        arrayResize(slots, length(literals), ''),
        arrayResize(arrayResize(values, length(slots), ''), length(literals), '')),
      '');

CREATE OR REPLACE FUNCTION tenx_inflate_core_iso AS (literals, slots, values) ->
    arrayStringConcat(
      arrayMap((lit, slot, val) -> concat(lit, tenx_substitute_slot_iso(val, slot)),
        literals,
        arrayResize(slots, length(literals), ''),
        arrayResize(arrayResize(values, length(slots), ''), length(literals), '')),
      '');

-- prep from elastic-hot-tier-budget/rig/fluent-bit/rig.lua, unchanged: the container moves into a
-- Kubernetes-style `kubernetes` map (container_name, docker_id); fb_ts is the event time.
function prep(tag, ts, rec)
  local c = rec["container_name"]
  if c then c = (string.gsub(c, "^/", "")) end
  local k = { container_name = c }
  if rec["container_id"] then k["docker_id"] = rec["container_id"] end
  rec["container_name"] = nil
  rec["container_id"] = nil
  rec["kubernetes"] = k
  rec["fb_ts"] = string.format("%.3f", ts)
  return 2, ts, rec
end

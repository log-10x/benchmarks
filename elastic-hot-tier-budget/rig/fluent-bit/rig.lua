-- Rig filters for Fluent Bit.
-- prep:  ingest from the Docker fluentd driver. The container moves into a Kubernetes-style
--        `kubernetes` map (container_name, docker_id), the shape Fluent Bit's kubernetes
--        filter gives a pod's records, where both the Receiver's fluentK8s extractor and the
--        MCP's file mode read the container. fb_ts is the driver's event time.
-- route: return path from the Receiver. rb_ts is the wall-clock time the record came back;
--        _route picks the file by routeState. service is the container (Datadog's service
--        tag, read by service_budgets); status is the Receiver's level, lower case.
local ok, ffi = pcall(require, "ffi")
local now
if ok then
  ffi.cdef[[ typedef struct { long tv_sec; long tv_usec; } rig_timeval; int gettimeofday(rig_timeval *tv, void *tz); ]]
  local tv = ffi.new("rig_timeval")
  now = function() ffi.C.gettimeofday(tv, nil); return tonumber(tv.tv_sec) + tonumber(tv.tv_usec) / 1e6 end
else
  now = function() return os.time() end
end

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

function route(tag, ts, rec)
  local r = rec["routeState"]
  if r == nil or r == "pass" then rec["_route"] = "pass"
  elseif r == "offload" or r == "tier_down" then rec["_route"] = r
  else rec["_route"] = "other" end
  rec["rb_ts"] = string.format("%.3f", now())
  local k = rec["kubernetes"]
  if type(k) == "table" and k["container_name"] then rec["service"] = k["container_name"] end
  if rec["severity_level"] then rec["status"] = string.lower(rec["severity_level"]) end
  return 2, ts, rec
end

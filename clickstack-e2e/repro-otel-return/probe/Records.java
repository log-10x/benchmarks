/** The six crafted messages, rendered in the shape OtlpLogsInputStream.renderRecord emits. */
public class Records {

    static final String[] NAMES = {
        "A plain, no escapes, resource",
        "B two escaped quotes, resource",
        "C five escaped quotes, resource",
        "D thirty escaped quotes, resource",
        "E one tab, resource",
        "F message is itself a JSON object, resource",
        "A plain, no escapes, NO resource",
        "B two escaped quotes, NO resource",
        "C five escaped quotes, NO resource",
        "D thirty escaped quotes, NO resource",
        "E one tab, NO resource",
        "F message is itself a JSON object, NO resource",
    };

    static String[] names() { return NAMES; }

    static String message(int i) {
        switch (i % 6) {
        case 0: return "[2025-10-01 20:34:05,556] INFO [ProducerStateManager partition=meta-0] Wrote snapshot at offset 2583 in 0 ms.";
        case 1: return "[2025-10-01 20:34:05,556] INFO consumer group \"alpha\" rebalanced in 0 ms.";
        case 2: return "[2025-10-01 20:34:05,556] INFO keys \"a\" \"b\" \"c\" \"d\" \"e\" settled.";
        case 3: { StringBuilder sb = new StringBuilder("[2025-10-01 20:34:05,556] INFO ");
                  for (int k = 0; k < 15; k++) sb.append("\"f").append(k).append("\" ");
                  return sb.append("settled.").toString(); }
        case 4: return "[2025-10-01 20:34:05,556] INFO\tcolumnar field separated by a tab.";
        default: return "{\"body\":\"inner\",\"level\":\"INFO\",\"k\":\"v\"}";
        }
    }

    static int escapes(int i) {
        String m = message(i);
        int n = 0;
        for (int k = 0; k < m.length(); k++) {
            char c = m.charAt(k);
            if (c == '"' || c == '\\' || c == '\t' || c == '\n' || c == '\r' || c < 0x20) n++;
        }
        return n;
    }

    static String esc(String s) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            switch (c) {
            case '"':  sb.append("\\\""); break;
            case '\\': sb.append("\\\\"); break;
            case '\t': sb.append("\\t"); break;
            case '\n': sb.append("\\n"); break;
            case '\r': sb.append("\\r"); break;
            default:
                if (c < 0x20) sb.append(String.format("\\u%04x", (int) c));
                else sb.append(c);
            }
        }
        return sb.toString();
    }

    static String recordWithMessage(String msg, boolean resource) {
        return build(esc(msg), resource);
    }

    static String record(int i) {
        return build(esc(message(i)), i < 6);
    }

    static String build(String escapedMessage, boolean resource) {
        StringBuilder sb = new StringBuilder();
        sb.append("{\"body\":\"").append(escapedMessage).append("\"");
        sb.append(",\"log.file.name\":\"slice.log\"");
        sb.append(",\"stream\":\"stdout\"");
        sb.append(",\"docker\":{\"container_id\":\"21f53b7ee51735caa49547e4db10d4c974f1161b940014174f069f2454f11d8c\"}");
        sb.append(",\"kubernetes\":{\"namespace_name\":\"default\",\"pod_name\":\"kafka-5ff8667569-jbfmv\",")
          .append("\"container_image_id\":\"ghcr.io/open-telemetry/demo@sha256:b91f13e3d4c26f70c2c56ff6c98ef3b1f0dee57accbc8d7fe096ce21b0a4cbc0\",")
          .append("\"pod_id\":\"4bdaf655-5d02-4653-ba57-fece182730aa\",\"host\":\"ip-192-168-42-205.ec2.internal\",")
          .append("\"labels\":{\"app.kubernetes.io/component\":\"kafka\",\"app.kubernetes.io/name\":\"kafka\",")
          .append("\"opentelemetry.io/name\":\"kafka\",\"pod-template-hash\":\"5ff8667569\"},")
          .append("\"container_name\":\"kafka\",\"container_image\":\"ghcr.io/open-telemetry/demo:2.1.3-kafka\",")
          .append("\"pod_ip\":\"192.168.37.206\"}");
        sb.append(",\"k8s_container\":\"kafka\"");
        sb.append(",\"k8s_namespace\":\"default\"");
        if (resource) sb.append(",\"service.name\":\"kafka\"");
        sb.append(",\"tag\":\"kafka\"");
        if (resource) sb.append(",\"_tenx_resource_keys\":[\"service.name\"]");
        sb.append(",\"_tenx_time\":0");
        sb.append(",\"_tenx_observed_time\":1757800000000000000");
        sb.append("}");
        return sb.toString();
    }
}

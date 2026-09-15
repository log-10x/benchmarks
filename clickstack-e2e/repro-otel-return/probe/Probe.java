import java.io.IOException;
import java.io.Reader;
import java.util.Map;
import jakarta.json.Json;
import jakarta.json.stream.JsonParser;
import jakarta.json.stream.JsonParser.Event;
import jakarta.json.stream.JsonParserFactory;
import org.eclipse.parsson.api.BufferPool;

/**
 * Replays com.log10x.eng.event.extract.EventJsonExtractor's offset arithmetic
 * over eclipse parsson 1.1.7, for the `drop:tag` action of the otel-collector
 * forwarder extractor. Prints the drop range it computes and the text that
 * survives it.
 */
public class Probe implements BufferPool {

    // ---- verbatim copy of com.log10x.eng.util.streams.reader.JsonStreamArrayCharReader
    static final class ArrayReader extends Reader {
        public char[] array;
        private int start, pos, length, remaining, syntheticCharsGenerated;
        private boolean isStreamStart, isEntryStart, hasAvailable;
        final boolean writeCommaAfterEOF;
        ArrayReader(boolean w) { this.writeCommaAfterEOF = w; restart(); }
        void restart() { isStreamStart = true; syntheticCharsGenerated = 0; set(null, -1, -1); }
        void set(char[] a, int s, int l) {
            array = a; start = s; pos = 0; length = l; remaining = l; hasAvailable = (l > 0);
        }
        public int read(char[] cbuf, int off, int len) throws IOException {
            if (isStreamStart) { cbuf[off] = '['; isStreamStart = false; syntheticCharsGenerated++; return 1; }
            if (writeCommaAfterEOF && isEntryStart) { cbuf[off] = ','; isEntryStart = false; return 1; }
            int toRead = Math.min(remaining, len);
            if (toRead > 0) {
                System.arraycopy(array, start + pos, cbuf, off, toRead);
                remaining -= toRead; pos += toRead;
                if (remaining == 0) isEntryStart = true;
                return toRead;
            }
            cbuf[off] = ','; isEntryStart = false; hasAvailable = false; return 1;
        }
        int start() { return start; }
        long syntheticCharsGenerated() { return syntheticCharsGenerated; }
        boolean hasAvailable() { return hasAvailable; }
        public void close() {}
    }

    private char[] buffer;
    public char[] take() { return buffer; }
    public void recycle(char[] b) {}

    static final int BASE_BUFFER_LEN = 2048;
    final ArrayReader reader = new ArrayReader(false);
    final JsonParserFactory factory;
    JsonParser parser;

    Probe() { factory = Json.createParserFactory(Map.of(BufferPool.class.getName(), this)); }

    private int findFieldStart(int end) {
        int r;
        for (r = end; r > 0; r--) {
            char c = reader.array[r - 1];
            if (c == ' ' || c == ',' || c == '{' || c == '"') break;
        }
        return r;
    }

    private int findMatchStart(int offset) {
        boolean foundQuote = false;
        for (int r = offset - 1; r >= reader.start(); r--) {
            char c = reader.array[r];
            if (c == ' ') continue;
            if (c == '"') { if (foundQuote) return -1; foundQuote = true; continue; }
            if (c == ',') { if (!foundQuote) return -1; return r; }
        }
        return -1;
    }

    private int findFirstFieldStart(int offset) {
        int quotePos = -1;
        for (int i = offset - 1; i >= reader.start(); i--) {
            char c = reader.array[i];
            if (c == ' ') continue;
            if (c == '"') { if (quotePos != -1) return -1; quotePos = i; continue; }
            if (c == '{') return quotePos;
            return -1;
        }
        return -1;
    }

    private int findTrailingComma(int offset) {
        for (int i = offset; i < reader.array.length; i++) {
            char c = reader.array[i];
            if (c == ' ') continue;
            return (c == ',') ? i : -1;
        }
        return -1;
    }

    /** Returns {dropStart, dropLength} for field `target`, or null. */
    int[] run(char[] array, int start, int length, String target, boolean verbose) throws IOException {
        int jsonStart = start, jsonLength = length;
        if (buffer == null || buffer.length < jsonLength) {
            buffer = new char[Math.max(jsonLength, BASE_BUFFER_LEN)];
            reader.restart();
            parser = null;
        }
        if (parser == null) parser = factory.createParser(reader);
        reader.set(array, jsonStart, jsonLength);

        boolean matchField = false;
        int scope = 0, matchStartPos = 0, scopeToCapture = 0;
        long baseStreamOffset = parser.getLocation().getStreamOffset();
        int readerStart = reader.start();
        int[] result = null;

        while (parser.hasNext()) {
            if (!reader.hasAvailable()) break;
            Event event = parser.next();
            long streamOffset = parser.getLocation().getStreamOffset();
            int readerOffset = (int) (streamOffset - baseStreamOffset + readerStart - reader.syntheticCharsGenerated());

            if (verbose) {
                System.out.printf("    %-14s streamOffset=%-6d readerOffset=%-5d ctx=[%s]%n",
                    event, streamOffset, readerOffset, ctx(array, readerOffset));
            }

            switch (event) {
            case KEY_NAME: {
                if (!matchField) {
                    int fieldEnd = readerOffset - 1;
                    int fieldStart = findFieldStart(fieldEnd);
                    String name = new String(array, fieldStart, Math.max(0, fieldEnd - fieldStart));
                    if (name.equals(target)) {
                        matchField = true; scopeToCapture = scope; matchStartPos = fieldStart;
                    }
                }
                break;
            }
            case START_OBJECT: case START_ARRAY: scope++; break;
            case END_OBJECT: case END_ARRAY: scope--; break;
            default: break;
            }

            if (matchField && scope == scopeToCapture &&
                (event == Event.VALUE_STRING || event == Event.VALUE_NUMBER ||
                 event == Event.VALUE_TRUE || event == Event.VALUE_FALSE || event == Event.VALUE_NULL)) {
                int matchEnd = readerOffset;
                int matchStart = findMatchStart(matchStartPos);
                if (matchStart != -1) {
                    result = new int[]{matchStart, matchEnd - matchStart};
                } else {
                    int firstStart = findFirstFieldStart(matchStartPos);
                    if (firstStart != -1) {
                        int tc = findTrailingComma(matchEnd);
                        int rangeEnd = (tc == -1) ? matchEnd : tc + 1;
                        result = new int[]{firstStart, rangeEnd - firstStart};
                    }
                }
                matchField = false; matchStartPos = 0; scopeToCapture = 0;
            }
        }
        return result;
    }

    static String ctx(char[] a, int off) {
        int s = Math.max(0, off - 6), e = Math.min(a.length, off + 6);
        if (off < 0 || off > a.length) return "OUT OF RANGE";
        return new String(a, s, off - s) + "|" + new String(a, off, e - off);
    }

    public static void main(String[] args) throws Exception {
        if (args.length > 0 && args[0].equals("sweep")) { sweep(); return; }
        boolean verbose = args.length > 0 && args[0].equals("-v");
        Probe p = new Probe();
        String[] names = Records.names();
        for (int i = 0; i < names.length; i++) {
            String rec = Records.record(i);
            char[] arr = rec.toCharArray();
            System.out.println("== " + names[i] + "  len=" + arr.length + " escapes=" + Records.escapes(i));
            if (verbose) System.out.println("  raw: " + rec);
            int[] r = p.run(arr, 0, arr.length, "tag", verbose);
            int trueStart = rec.indexOf(",\"tag\":");
            int trueEnd = rec.indexOf('"', rec.indexOf(':', trueStart) + 2) + 1;
            if (r == null) {
                System.out.println("  NO DROP RANGE (field not matched). trueStart=" + trueStart);
            } else {
                System.out.printf("  drop=[%d,%d) len=%d   true=[%d,%d) len=%d   shift=%d  lenDelta=%d%n",
                    r[0], r[0] + r[1], r[1], trueStart, trueEnd, trueEnd - trueStart,
                    r[0] - trueStart, r[1] - (trueEnd - trueStart));
                StringBuilder sb = new StringBuilder(rec);
                sb.delete(r[0], r[0] + r[1]);
                String out = sb.toString();
                System.out.println("  after drop: " + tail(out));
                boolean ok = isParseable(out);
                System.out.println("  parses=" + ok + "  keys=" + keys(out));
            }
        }
    }

    /** Pre-roll of W chars, then the test record; report the shift of the drop range. */
    static void sweep() throws Exception {
        int[] escapeCounts = {0, 1, 2, 5, 30};
        int trials = 0, divergences = 0;
        System.out.println("E\tpreroll\tshift\tlenDelta\tparses\tkeysAfterTag");
        for (int e : escapeCounts) {
            String msg = buildMsg(e);
            for (int w = 0; w <= 2600; w++) {
                Probe p = new Probe();
                String pre = Records.record(0).replace("[2025-10-01", pad(w) + "[2025-10-01");
                char[] pa = pre.toCharArray();
                p.run(pa, 0, pa.length, "tag", false);
                String rec = Records.recordWithMessage(msg, true);
                char[] arr = rec.toCharArray();
                int[] r = p.run(arr, 0, arr.length, "tag", false);
                int trueStart = rec.indexOf(",\"tag\":");
                int trueEnd = rec.indexOf('"', rec.indexOf(':', trueStart) + 2) + 1;
                int shift = (r == null) ? Integer.MIN_VALUE : r[0] - trueStart;
                int lenDelta = (r == null) ? 0 : r[1] - (trueEnd - trueStart);
                trials++;
                if (shift == 0 && lenDelta == 0) continue;
                divergences++;
                String out;
                boolean parses;
                String ks;
                if (r == null) { out = rec; parses = true; ks = "NO DROP"; }
                else {
                    StringBuilder sb = new StringBuilder(rec);
                    sb.delete(r[0], Math.min(rec.length(), r[0] + r[1]));
                    out = sb.toString(); parses = isParseable(out); ks = keys(out);
                }
                System.out.println(e + "\t" + w + "\t" + (r == null ? "NOMATCH" : String.valueOf(shift))
                    + "\t" + lenDelta + "\t" + parses + "\t" + ks);
            }
        }
        System.out.println("trials=" + trials + " divergences=" + divergences);
    }

    static String pad(int n) { StringBuilder sb = new StringBuilder(); for (int i = 0; i < n; i++) sb.append('x'); return sb.toString(); }

    static String buildMsg(int e) {
        StringBuilder sb = new StringBuilder("[2025-10-01 20:34:05,556] INFO ");
        for (int i = 0; i < e; i++) sb.append('"');
        sb.append(" settled.");
        return sb.toString();
    }

    static String tail(String s) {
        int i = s.length() - 140;
        return (i > 0 ? "..." + s.substring(i) : s);
    }

    static boolean isParseable(String s) {
        try (JsonParser jp = Json.createParser(new java.io.StringReader(s))) {
            while (jp.hasNext()) jp.next();
            return true;
        } catch (Exception e) { return false; }
    }

    static String keys(String s) {
        try (JsonParser jp = Json.createParser(new java.io.StringReader(s))) {
            StringBuilder sb = new StringBuilder();
            int depth = 0;
            while (jp.hasNext()) {
                Event e = jp.next();
                if (e == Event.START_OBJECT || e == Event.START_ARRAY) depth++;
                else if (e == Event.END_OBJECT || e == Event.END_ARRAY) depth--;
                else if (e == Event.KEY_NAME && depth == 1) sb.append(jp.getString()).append(' ');
            }
            return sb.toString().trim();
        } catch (Exception e) { return "UNPARSEABLE"; }
    }
}

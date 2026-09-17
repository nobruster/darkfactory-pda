package com.northwindpay.legacy.type01;

import com.fasterxml.jackson.databind.JsonNode;
import com.northwindpay.legacy.core.ArtifactIO;
import com.northwindpay.legacy.core.BatchProcessor;
import com.northwindpay.legacy.core.DiagnosticPrivacy;
import com.northwindpay.legacy.core.ProcessingContext;
import com.northwindpay.legacy.core.ProcessorException;
import com.northwindpay.legacy.core.ProcessorResult;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.security.MessageDigest;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.time.format.ResolverStyle;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.regex.Pattern;

/**
 * Strict fixed-width Type 01 card-settlement converter.
 */
public final class Type01Processor implements BatchProcessor {
    private static final Pattern BATCH_PATTERN = Pattern.compile("B[0-9]{15}");
    private static final Pattern FILENAME_PATTERN = Pattern.compile(
            "NW_CARD_SETTLEMENT_[0-9]{8}_B[0-9]{15}\\.dat");
    private static final Pattern IDENTIFIER_PATTERN = Pattern.compile("[A-Z0-9]{16}");
    private static final Pattern DIGITS_16 = Pattern.compile("[0-9]{16}");
    private static final Pattern DIGITS_12 = Pattern.compile("[0-9]{12}");
    private static final Pattern DIGITS_11 = Pattern.compile("[0-9]{11}");
    private static final Pattern AUTH_PATTERN = Pattern.compile("[A-Z0-9]{6}");
    private static final Pattern CANONICAL_MONEY_PATTERN = Pattern.compile(
            "-?(?:0|[1-9][0-9]{0,15})\\.[0-9]{2}");
    private static final String POSITIVE_OVERPUNCH = "{ABCDEFGHI";
    private static final String NEGATIVE_OVERPUNCH = "}JKLMNOPQR";
    private static final DateTimeFormatter DATE_FORMATTER =
            DateTimeFormatter.ofPattern("uuuuMMdd", Locale.ROOT)
                    .withResolverStyle(ResolverStyle.STRICT);
    private static final DateTimeFormatter TIME_FORMATTER =
            DateTimeFormatter.ofPattern("HHmmss", Locale.ROOT)
                    .withResolverStyle(ResolverStyle.STRICT);
    private static final ZoneId SAO_PAULO = ZoneId.of("America/Sao_Paulo");
    private static final String CSV_HEADER = String.join(",",
            "batch_id",
            "source_file",
            "source_record_number",
            "transaction_id",
            "merchant_id",
            "card_token",
            "card_last4",
            "cpf_masked",
            "transaction_ts",
            "amount_brl",
            "movement_code",
            "authorization_code",
            "nsu",
            "terminal_id");

    /**
     * Creates the stateless Type 01 processor.
     */
    public Type01Processor() {
    }

    @Override
    public String typeNumber() {
        return "01";
    }

    @Override
    public String typeCode() {
        return "CRD_SETTLE01";
    }

    @Override
    public String layoutVersion() {
        return "001";
    }

    @Override
    public ProcessorResult process(ProcessingContext context)
            throws ProcessorException {
        DiagnosticPrivacy privacy = diagnosticPrivacyForRaw(
                context.sourceArtifact().bytes());
        try {
            return processProtected(context);
        } catch (ProcessorException exception) {
            throw exception.withDiagnosticPrivacy(privacy);
        }
    }

    private ProcessorResult processProtected(ProcessingContext context)
            throws ProcessorException {
        String batchId = context.batchId();
        if (!BATCH_PATTERN.matcher(batchId).matches()) {
            throw new ProcessorException("INVALID_BATCH_ID", "Batch ID does not match the Type 01 contract");
        }

        byte[] sourceManifest = context.sourceManifestBytes();
        JsonNode manifest = context.sourceManifest();
        SourceDescriptor source = validateManifest(manifest, batchId);
        ProcessingContext.SourceArtifact artifact =
                context.sourceArtifact();
        if (!source.filename().equals(artifact.filename())
                || !source.sha256().equals(artifact.sha256())
                || source.sizeBytes() != artifact.sizeBytes()) {
            throw new ProcessorException(
                    "INVALID_MANIFEST",
                    "Acquired source does not match Type 01 metadata");
        }
        byte[] rawBytes = artifact.bytes();
        ParsedBatch parsed = parseRaw(rawBytes, source.filename(), batchId);
        validateSourceControls(parsed, manifest);

        CsvOutput output = renderCsv(
                parsed,
                source.filename(),
                context.configuration().tokenizationKey());
        String csvFilename = source.filename().substring(0, source.filename().length() - 4) + ".csv";
        String csvSha256 = sha256(output.bytes());

        Map<String, Object> sanitizedManifest = sanitizedManifest(
                batchId,
                source,
                sourceManifest,
                csvFilename,
                csvSha256,
                output);
        ArtifactIO.PublishedCsv published = ArtifactIO.publishSanitized(
                context,
                csvFilename,
                output.bytes(),
                sanitizedManifest);

        return ProcessorResult.type01Succeeded(
                batchId,
                published.filename(),
                published.sha256(),
                output.rowCount(),
                money(output.netAmountMinor()));
    }

    private static SourceDescriptor validateManifest(JsonNode manifest, String batchId)
            throws ProcessorException {
        if (!manifest.isObject()
                || manifest.path("schema_version").asInt(-1) != 1
                || !batchId.equals(manifest.path("batch_id").asText())
                || !"01".equals(manifest.path("file_type").path("number").asText())
                || !"CRD_SETTLE01".equals(manifest.path("file_type").path("code").asText())
                || !manifest.path("file_type").path("contract_version").isIntegralNumber()
                || manifest.path("file_type").path("contract_version").intValue() != 1
                || !"001".equals(manifest.path("file_type").path("layout_version").asText())) {
            throw new ProcessorException("INVALID_MANIFEST", "Source manifest does not match Type 01");
        }
        JsonNode sourceFile = manifest.path("source_file");
        String filename = sourceFile.path("name").asText();
        String sha256 = sourceFile.path("sha256").asText();
        long sizeBytes = sourceFile.path("size_bytes").asLong(-1);
        if (!FILENAME_PATTERN.matcher(filename).matches()
                || !filename.contains(batchId)
                || !sha256.matches("[0-9a-f]{64}")
                || sizeBytes < 1
                || !"ISO-8859-1".equals(sourceFile.path("encoding").asText())
                || !"LF".equals(sourceFile.path("line_ending").asText())
                || !"required".equals(sourceFile.path("final_newline").asText())) {
            throw new ProcessorException("INVALID_MANIFEST", "Source file metadata violates Type 01");
        }
        return new SourceDescriptor(filename, sha256, sizeBytes);
    }

    static ParsedBatch parseRaw(byte[] rawBytes, String sourceFilename, String expectedBatchId)
            throws ProcessorException {
        DiagnosticPrivacy privacy =
                diagnosticPrivacyForRaw(rawBytes);
        try {
            return parseRawProtected(
                    rawBytes,
                    sourceFilename,
                    expectedBatchId,
                    privacy);
        } catch (ProcessorException exception) {
            throw exception.withDiagnosticPrivacy(privacy);
        }
    }

    private static ParsedBatch parseRawProtected(
            byte[] rawBytes,
            String sourceFilename,
            String expectedBatchId,
            DiagnosticPrivacy privacy) throws ProcessorException {
        if (rawBytes.length == 0
                || rawBytes[rawBytes.length - 1] != '\n'
                || contains(rawBytes, (byte) '\r')) {
            throw new ProcessorException("INVALID_TRANSPORT", "Type 01 requires LF records and one final LF");
        }

        String content = new String(rawBytes, StandardCharsets.ISO_8859_1);
        String[] split = content.split("\\n", -1);
        if (!split[split.length - 1].isEmpty()) {
            throw new ProcessorException("INVALID_TRANSPORT", "Type 01 requires a final LF");
        }
        List<String> records = List.of(split).subList(0, split.length - 1);
        if (records.size() < 3) {
            throw new ProcessorException("INVALID_RECORD_SEQUENCE", "Type 01 requires H, D+, T records");
        }
        return parseRecords(
                records,
                sourceFilename,
                expectedBatchId,
                privacy);
    }

    private static ParsedBatch parseRecords(
            List<String> records,
            String sourceFilename,
            String expectedBatchId,
            DiagnosticPrivacy privacy) throws ProcessorException {
        String header = records.getFirst();
        String trailer = records.getLast();
        requireLength(header, 40, 1);
        requireLength(trailer, 46, records.size());
        if (header.charAt(0) != 'H' || trailer.charAt(0) != 'T') {
            throw new ProcessorException("INVALID_RECORD_SEQUENCE", "Header or trailer discriminator is invalid");
        }

        String fileDate = header.substring(1, 9);
        String batchId = header.substring(9, 25);
        requireDate(fileDate, 1, null);
        if (!BATCH_PATTERN.matcher(batchId).matches()
                || !expectedBatchId.equals(batchId)
                || !"CRD_SETTLE01".equals(header.substring(25, 37))
                || !"001".equals(header.substring(37, 40))
                || !sourceFilename.equals("NW_CARD_SETTLEMENT_" + fileDate + "_" + batchId + ".dat")
                || !batchId.substring(1, 9).equals(fileDate)) {
            throw new ProcessorException("HEADER_MISMATCH", "Header, filename, and requested batch do not agree");
        }

        List<Detail> details = new ArrayList<>();
        Set<String> transactionIds = new HashSet<>();
        long computedNet = 0;
        for (int index = 1; index < records.size() - 1; index++) {
            int recordNumber = index + 1;
            Detail detail = parseDetail(
                    records.get(index),
                    recordNumber,
                    privacy);
            if (!transactionIds.add(detail.transactionId())) {
                throw new ProcessorException(
                        "DUPLICATE_TRANSACTION_ID",
                        "Duplicate transaction ID in batch",
                        recordNumber,
                        privacySafeTransactionId(
                                detail.transactionId(),
                                detail.pan(),
                                detail.cpf()))
                        .withDiagnosticPrivacy(privacy);
            }
            computedNet = Math.addExact(computedNet, detail.amountMinor());
            details.add(detail);
        }

        String trailerDate = trailer.substring(1, 9);
        String declaredCountText = trailer.substring(9, 15);
        if (!declaredCountText.matches("[0-9]{6}")) {
            throw new ProcessorException(
                    "INVALID_TRAILER",
                    "Trailer count is invalid");
        }
        int declaredCount;
        try {
            declaredCount = Integer.parseInt(declaredCountText);
        } catch (NumberFormatException exception) {
            throw new ProcessorException("INVALID_TRAILER", "Trailer count is invalid");
        }
        long declaredNet = decodeOverpunch(trailer.substring(15, 30), records.size(), null);
        String trailerBatch = trailer.substring(30, 46);
        if (!fileDate.equals(trailerDate) || !batchId.equals(trailerBatch)) {
            throw new ProcessorException("TRAILER_MISMATCH", "Header and trailer do not agree");
        }

        return new ParsedBatch(
                batchId,
                fileDate,
                List.copyOf(details),
                declaredCount,
                declaredNet,
                computedNet);
    }

    private static Detail parseDetail(
            String record,
            int recordNumber,
            DiagnosticPrivacy privacy)
            throws ProcessorException {
        requireLength(record, 124, recordNumber);
        if (record.charAt(0) != 'D') {
            throw new ProcessorException("INVALID_RECORD_SEQUENCE", "Detail discriminator is invalid", recordNumber, null);
        }
        String transactionId = record.substring(1, 17);
        String merchantId = record.substring(17, 33);
        String pan = record.substring(33, 49);
        String cpf = record.substring(49, 60);
        String date = record.substring(60, 68);
        String time = record.substring(68, 74);
        String amountText = record.substring(74, 86);
        String currency = record.substring(86, 89);
        String movement = record.substring(89, 90);
        String authorizationCode = record.substring(90, 96);
        String nsu = record.substring(96, 108);
        String terminalId = record.substring(108, 124);
        String diagnosticTransactionId =
                privacy.redact(
                        privacySafeTransactionId(
                                transactionId,
                                pan,
                                cpf));

        if (!IDENTIFIER_PATTERN.matcher(transactionId).matches()
                || !IDENTIFIER_PATTERN.matcher(merchantId).matches()
                || !DIGITS_16.matcher(pan).matches()
                || !DIGITS_11.matcher(cpf).matches()
                || !"BRL".equals(currency)
                || !AUTH_PATTERN.matcher(authorizationCode).matches()
                || !DIGITS_12.matcher(nsu).matches()
                || !IDENTIFIER_PATTERN.matcher(terminalId).matches()) {
            throw new ProcessorException(
                    "INVALID_DETAIL",
                    "Detail fields violate Type 01",
                    recordNumber,
                    diagnosticTransactionId);
        }
        requireDate(date, recordNumber, diagnosticTransactionId);
        requireTime(time, recordNumber, diagnosticTransactionId);
        long amountMinor = decodeOverpunch(
                amountText,
                recordNumber,
                diagnosticTransactionId);
        if (("P".equals(movement) && amountMinor <= 0)
                || ("R".equals(movement) && amountMinor >= 0)
                || (!"P".equals(movement) && !"R".equals(movement))) {
            throw new ProcessorException(
                    "INVALID_MOVEMENT_AMOUNT",
                    "Movement and amount sign do not agree",
                    recordNumber,
                    diagnosticTransactionId);
        }
        return new Detail(
                recordNumber,
                transactionId,
                merchantId,
                pan,
                cpf,
                date,
                time,
                amountMinor,
                movement,
                authorizationCode,
                nsu,
                terminalId);
    }

    static long decodeOverpunch(String encoded, int recordNumber, String transactionId)
            throws ProcessorException {
        if (encoded.length() < 2 || !encoded.substring(0, encoded.length() - 1).matches("[0-9]+")) {
            throw new ProcessorException("INVALID_OVERPUNCH", "Amount overpunch is invalid", recordNumber, transactionId);
        }
        char signCharacter = encoded.charAt(encoded.length() - 1);
        int digit = POSITIVE_OVERPUNCH.indexOf(signCharacter);
        int sign = 1;
        if (digit < 0) {
            digit = NEGATIVE_OVERPUNCH.indexOf(signCharacter);
            sign = -1;
        }
        if (digit < 0) {
            throw new ProcessorException("INVALID_OVERPUNCH", "Amount overpunch is invalid", recordNumber, transactionId);
        }
        try {
            long absolute = Long.parseLong(encoded.substring(0, encoded.length() - 1) + digit);
            return Math.multiplyExact(absolute, sign);
        } catch (ArithmeticException | NumberFormatException exception) {
            throw new ProcessorException("INVALID_OVERPUNCH", "Amount overpunch is outside supported range", recordNumber, transactionId);
        }
    }

    static void validateSourceControls(ParsedBatch parsed, JsonNode manifest)
            throws ProcessorException {
        DiagnosticPrivacy privacy =
                diagnosticPrivacyForDetails(parsed.details());
        JsonNode controls = manifest == null
                ? null
                : manifest.get("source_controls");
        if (controls == null
                || !controls.isObject()
                || controls.size() != 3) {
            throw new ProcessorException(
                    "INVALID_MANIFEST",
                    "Type 01 source controls are invalid")
                    .withDiagnosticPrivacy(privacy);
        }
        JsonNode currency = controls.get("currency");
        JsonNode detailCount = controls.get("detail_count");
        JsonNode netAmount = controls.get("net_amount");
        if (currency == null
                || !currency.isTextual()
                || !"BRL".equals(currency.textValue())
                || detailCount == null
                || !detailCount.isIntegralNumber()
                || !detailCount.canConvertToInt()
                || detailCount.intValue() < 1
                || detailCount.intValue() > 999_999
                || netAmount == null
                || !netAmount.isTextual()
                || !CANONICAL_MONEY_PATTERN.matcher(
                        netAmount.textValue()).matches()
                || "-0.00".equals(netAmount.textValue())) {
            throw new ProcessorException(
                    "INVALID_MANIFEST",
                    "Type 01 source controls are invalid")
                    .withDiagnosticPrivacy(privacy);
        }
        int manifestCount = detailCount.intValue();
        String manifestNet = netAmount.textValue();
        if (manifestCount != parsed.declaredCount()
                || !money(parsed.declaredNetMinor()).equals(manifestNet)
                || parsed.declaredCount() != parsed.details().size()
                || parsed.declaredNetMinor() != parsed.computedNetMinor()) {
            throw ProcessorException.type01SourceControlMismatch(
                    parsed.declaredCount(),
                    money(parsed.declaredNetMinor()),
                    parsed.details().size(),
                    money(parsed.computedNetMinor()),
                    parsed.details().stream()
                            .map(detail -> money(detail.amountMinor()))
                            .toList())
                    .withDiagnosticPrivacy(privacy);
        }
    }

    static CsvOutput renderCsv(ParsedBatch parsed, String sourceFilename, String key)
            throws ProcessorException {
        DiagnosticPrivacy privacy =
                diagnosticPrivacyForDetails(parsed.details());
        try {
            return renderCsvProtected(parsed, sourceFilename, key);
        } catch (ProcessorException exception) {
            throw exception.withDiagnosticPrivacy(privacy);
        }
    }

    private static CsvOutput renderCsvProtected(
            ParsedBatch parsed,
            String sourceFilename,
            String key) throws ProcessorException {
        if (key == null || key.isBlank()) {
            throw new ProcessorException("TOKENIZATION_KEY_MISSING", "Tokenization key is required");
        }
        StringBuilder csv = new StringBuilder(CSV_HEADER).append('\n');
        for (Detail detail : parsed.details()) {
            LocalDate date = LocalDate.parse(detail.date(), DATE_FORMATTER);
            LocalTime time = LocalTime.parse(detail.time(), TIME_FORMATTER);
            String timestamp = LocalDateTime.of(date, time)
                    .atZone(SAO_PAULO)
                    .toOffsetDateTime()
                    .format(DateTimeFormatter.ISO_OFFSET_DATE_TIME);
            List<String> fields = List.of(
                    parsed.batchId(),
                    sourceFilename,
                    Integer.toString(detail.recordNumber()),
                    detail.transactionId(),
                    detail.merchantId(),
                    tokenize(detail.pan(), key),
                    detail.pan().substring(12),
                    "*******" + detail.cpf().substring(7),
                    timestamp,
                    money(detail.amountMinor()),
                    detail.movement(),
                    detail.authorizationCode(),
                    detail.nsu(),
                    detail.terminalId());
            csv.append(fields.stream().map(Type01Processor::csvField).reduce((left, right) -> left + "," + right).orElseThrow())
                    .append('\n');
        }
        String rendered = csv.toString();
        validatePrivacyBoundary(rendered, parsed.details());
        return new CsvOutput(
                rendered.getBytes(StandardCharsets.UTF_8),
                parsed.details().size(),
                parsed.computedNetMinor());
    }

    private static void validatePrivacyBoundary(
            String renderedCsv,
            List<Detail> details) throws ProcessorException {
        for (Detail detail : details) {
            if (renderedCsv.contains(detail.pan())
                    || renderedCsv.contains(detail.cpf())) {
                throw new ProcessorException(
                        "PRIVACY_BOUNDARY_VIOLATION",
                        "Sanitized CSV contains a restricted raw identifier",
                        detail.recordNumber(),
                        null);
            }
        }
    }

    private static Map<String, Object> sanitizedManifest(
            String batchId,
            SourceDescriptor source,
            byte[] sourceManifest,
            String csvFilename,
            String csvSha256,
            CsvOutput output) {
        Map<String, Object> csvFile = Map.of(
                "encoding", "UTF-8",
                "name", csvFilename,
                "row_count", output.rowCount(),
                "sha256", csvSha256,
                "size_bytes", output.bytes().length);
        Map<String, Object> fileType = Map.of(
                "code", "CRD_SETTLE01",
                "contract_version", 1,
                "layout_version", "001",
                "number", "01");
        Map<String, Object> lineage = Map.of(
                "manifest_sha256", sha256(sourceManifest),
                "raw_file", source.filename(),
                "raw_sha256", source.sha256());
        Map<String, Object> controls = Map.of(
                "currency", "BRL",
                "net_amount", money(output.netAmountMinor()),
                "row_count", output.rowCount());
        return Map.of(
                "batch_id", batchId,
                "csv_file", csvFile,
                "file_type", fileType,
                "schema_version", 1,
                "source_lineage", lineage,
                "stage_controls", controls);
    }

    private static String tokenize(String pan, String key) throws ProcessorException {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(key.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
            byte[] digest = mac.doFinal(pan.getBytes(StandardCharsets.US_ASCII));
            return "tok_" + java.util.HexFormat.of().formatHex(digest).substring(0, 24);
        } catch (GeneralSecurityException exception) {
            throw new ProcessorException("TOKENIZATION_ERROR", "Cannot tokenize protected field", exception);
        }
    }

    static String sha256(byte[] content) {
        try {
            return java.util.HexFormat.of().formatHex(
                    MessageDigest.getInstance("SHA-256").digest(content));
        } catch (GeneralSecurityException exception) {
            throw new IllegalStateException("SHA-256 is unavailable", exception);
        }
    }

    static String money(long minor) {
        return BigDecimal.valueOf(minor, 2)
                .setScale(2, RoundingMode.UNNECESSARY)
                .toPlainString();
    }

    private static String csvField(String value) {
        if (value.indexOf(',') >= 0 || value.indexOf('"') >= 0 || value.indexOf('\n') >= 0 || value.indexOf('\r') >= 0) {
            return "\"" + value.replace("\"", "\"\"") + "\"";
        }
        return value;
    }

    private static String privacySafeTransactionId(
            String transactionId,
            String pan,
            String cpf) {
        if (transactionId.contains(pan)
                || transactionId.contains(cpf)) {
            return null;
        }
        return transactionId;
    }

    private static DiagnosticPrivacy diagnosticPrivacyForRaw(
            byte[] rawBytes) {
        String raw = new String(
                rawBytes,
                StandardCharsets.ISO_8859_1);
        return diagnosticPrivacyForRecords(
                List.of(raw.split("\\n", -1)));
    }

    private static DiagnosticPrivacy diagnosticPrivacyForRecords(
            List<String> records) {
        List<String> restrictedValues = new ArrayList<>();
        for (String record : records) {
            if (record.length() >= 60
                    && record.charAt(0) == 'D') {
                restrictedValues.add(record.substring(33, 49));
                restrictedValues.add(record.substring(49, 60));
            }
        }
        return DiagnosticPrivacy.fromRestrictedValues(
                restrictedValues);
    }

    private static DiagnosticPrivacy diagnosticPrivacyForDetails(
            List<Detail> details) {
        List<String> restrictedValues =
                new ArrayList<>(details.size() * 2);
        for (Detail detail : details) {
            restrictedValues.add(detail.pan());
            restrictedValues.add(detail.cpf());
        }
        return DiagnosticPrivacy.fromRestrictedValues(
                restrictedValues);
    }

    private static void requireLength(String value, int expected, int recordNumber)
            throws ProcessorException {
        if (value.length() != expected) {
            throw new ProcessorException("INVALID_RECORD_LENGTH", "Record has the wrong byte length", recordNumber, null);
        }
    }

    private static void requireDate(String value, int recordNumber, String transactionId)
            throws ProcessorException {
        try {
            LocalDate.parse(value, DATE_FORMATTER);
        } catch (RuntimeException exception) {
            throw new ProcessorException("INVALID_DATE", "Date is invalid", recordNumber, transactionId);
        }
    }

    private static void requireTime(String value, int recordNumber, String transactionId)
            throws ProcessorException {
        try {
            LocalTime.parse(value, TIME_FORMATTER);
        } catch (RuntimeException exception) {
            throw new ProcessorException("INVALID_TIME", "Time is invalid", recordNumber, transactionId);
        }
    }

    private static boolean contains(byte[] content, byte target) {
        for (byte value : content) {
            if (value == target) {
                return true;
            }
        }
        return false;
    }

    record SourceDescriptor(String filename, String sha256, long sizeBytes) {
    }

    record Detail(
            int recordNumber,
            String transactionId,
            String merchantId,
            String pan,
            String cpf,
            String date,
            String time,
            long amountMinor,
            String movement,
            String authorizationCode,
            String nsu,
            String terminalId) {
    }

    record ParsedBatch(
            String batchId,
            String fileDate,
            List<Detail> details,
            int declaredCount,
            long declaredNetMinor,
            long computedNetMinor) {
    }

    record CsvOutput(byte[] bytes, int rowCount, long netAmountMinor) {
    }
}

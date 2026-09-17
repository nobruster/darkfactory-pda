package com.northwindpay.legacy.type02;

import com.fasterxml.jackson.databind.JsonNode;
import com.northwindpay.legacy.core.ArtifactIO;
import com.northwindpay.legacy.core.BatchProcessor;
import com.northwindpay.legacy.core.ProcessingContext;
import com.northwindpay.legacy.core.ProcessorException;
import com.northwindpay.legacy.core.ProcessorResult;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.math.BigDecimal;
import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.text.Normalizer;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.time.format.ResolverStyle;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Contract-faithful Type 02 instant-payment event converter.
 *
 * <p>The implementation treats the source as hostile: transport and UTF-8 are
 * checked before parsing, escaping is decoded exactly once, decimal arithmetic
 * is exact, and restricted document values cross the sanitization boundary
 * only as independently keyed HMAC tokens and last-four masks.
 */
public final class Type02Processor implements BatchProcessor {
    private static final int MAX_SOURCE_BYTES = 5_200_000;
    private static final int MAX_RECORD_BYTES = 512;
    private static final int MAX_EVENTS = 10_000;
    private static final int MAX_CSV_BYTES = 6_000_000;
    private static final Pattern BATCH_PATTERN =
            Pattern.compile("B[0-9]{15}");
    private static final Pattern FILENAME_PATTERN = Pattern.compile(
            "NW_INSTANT_PAYMENT_([0-9]{8})_(B[0-9]{15})\\.txt");
    private static final Pattern END_TO_END_PATTERN =
            Pattern.compile("E[0-9]{31}");
    private static final Pattern TRANSACTION_PATTERN =
            Pattern.compile("(?=[A-Z0-9]{16}\\z)(?=[A-Z0-9]*[A-Z])[A-Z0-9]+");
    private static final Pattern UNSIGNED_MONEY_PATTERN =
            Pattern.compile("(?:0|[1-9][0-9]{0,15})\\.[0-9]{2}");
    private static final Pattern SIGNED_MONEY_PATTERN =
            Pattern.compile("-?(?:0|[1-9][0-9]{0,15})\\.[0-9]{2}");
    private static final Pattern RETURN_CODE_PATTERN =
            Pattern.compile("[A-Z0-9]{1,4}");
    private static final Pattern TIMESTAMP_PATTERN = Pattern.compile(
            "[0-9]{4}-[0-9]{2}-[0-9]{2}T"
                    + "[0-9]{2}:[0-9]{2}:[0-9]{2}"
                    + "(?:Z|[+-][0-9]{2}:[0-9]{2})");
    private static final Pattern RESTRICTED_DIGIT_RUN =
            Pattern.compile("[0-9]{11,19}");
    private static final DateTimeFormatter FILE_DATE_FORMATTER =
            DateTimeFormatter.ofPattern("uuuuMMdd", Locale.ROOT)
                    .withResolverStyle(ResolverStyle.STRICT);
    private static final ZoneId SAO_PAULO =
            ZoneId.of("America/Sao_Paulo");
    private static final BigDecimal ZERO = new BigDecimal("0.00");
    private static final String CSV_HEADER = String.join(",",
            "batch_id",
            "source_file",
            "source_record_number",
            "end_to_end_id",
            "transaction_id",
            "payer_document_token",
            "payer_document_masked",
            "payee_document_token",
            "payee_document_masked",
            "event_timestamp",
            "amount_brl",
            "direction",
            "status",
            "return_code",
            "description");

    @Override
    public String typeNumber() {
        return "02";
    }

    @Override
    public String typeCode() {
        return "PIX_EVENTS01";
    }

    @Override
    public String layoutVersion() {
        return "001";
    }

    /**
     * Validates, sanitizes, and atomically publishes one Type 02 source.
     */
    @Override
    public ProcessorResult process(ProcessingContext context)
            throws ProcessorException {
        String documentKey =
                context.configuration().documentTokenKey();
        if (documentKey == null || documentKey.isBlank()) {
            throw new ProcessorException(
                    "DOCUMENT_TOKEN_KEY_MISSING",
                    "Type 02 document tokenization key is required");
        }

        SourceDescriptor source = validateManifest(
                context.sourceManifest(),
                context.batchId());
        ProcessingContext.SourceArtifact artifact =
                context.sourceArtifact();
        if (!source.filename().equals(artifact.filename())
                || !source.sha256().equals(artifact.sha256())
                || source.sizeBytes() != artifact.sizeBytes()) {
            throw new ProcessorException(
                    "INVALID_MANIFEST",
                    "Acquired source does not match Type 02 metadata");
        }

        ParsedBatch parsed = parseRaw(
                artifact.bytes(),
                source.filename(),
                context.batchId());
        validateSourceControls(
                parsed,
                context.sourceManifest());
        CsvOutput csv = renderCsv(
                parsed,
                source.filename(),
                documentKey);
        String csvFilename = source.filename().substring(
                0,
                source.filename().length() - ".txt".length()) + ".csv";
        String csvSha256 = ArtifactIO.sha256(csv.bytes());
        Map<String, Object> sanitizedManifest = sanitizedManifest(
                context,
                source,
                csvFilename,
                csvSha256,
                csv);
        ArtifactIO.PublishedCsv published =
                ArtifactIO.publishSanitized(
                        context,
                        csvFilename,
                        csv.bytes(),
                        sanitizedManifest);
        return ProcessorResult.type02Succeeded(
                context.batchId(),
                published.filename(),
                published.sha256(),
                csv.rowCount(),
                money(csv.creditAmount()),
                money(csv.debitAmount()),
                money(csv.netAmount()),
                csv.returnedCount());
    }

    static ParsedBatch parseRaw(
            byte[] rawBytes,
            String sourceFilename,
            String expectedBatchId) throws ProcessorException {
        String text = decodeTransport(rawBytes);
        String[] lines = text.substring(0, text.length() - 1)
                .split("\\n", -1);
        if (lines.length < 3) {
            throw new ProcessorException(
                    "INVALID_RECORD_SEQUENCE",
                    "Type 02 requires one header, events, and one trailer");
        }
        if (lines.length - 2 > MAX_EVENTS) {
            throw new ProcessorException(
                    "INVALID_TRANSPORT",
                    "Type 02 event limit is exceeded");
        }
        for (String line : lines) {
            if (line.isEmpty()) {
                throw new ProcessorException(
                        "INVALID_TRANSPORT",
                        "Type 02 forbids blank physical records");
            }
        }

        List<String> header = lex(lines[0], 1);
        List<String> trailer = lex(lines[lines.length - 1], lines.length);
        if (header.size() != 5
                || !"H".equals(header.get(0))
                || !"PIX_EVENTS01".equals(header.get(1))
                || !"001".equals(header.get(2))
                || trailer.size() != 5
                || !"T".equals(trailer.get(0))) {
            throw new ProcessorException(
                    "INVALID_RECORD_SEQUENCE",
                    "Type 02 header or trailer is invalid");
        }

        LocalDate fileDate = parseFileDate(header.get(3));
        String batchId = header.get(4);
        Matcher filename = FILENAME_PATTERN.matcher(sourceFilename);
        if (!filename.matches()
                || !BATCH_PATTERN.matcher(batchId).matches()
                || !expectedBatchId.equals(batchId)
                || !header.get(3).equals(filename.group(1))
                || !batchId.equals(filename.group(2))
                || !batchId.substring(1, 9).equals(header.get(3))) {
            throw new ProcessorException(
                    "INVALID_RECORD_SEQUENCE",
                    "Header, filename, and requested batch do not agree");
        }

        List<Event> events = new ArrayList<>();
        Set<String> endToEndIds = new HashSet<>();
        Set<String> transactionIds = new HashSet<>();
        BigDecimal computedCredit = ZERO;
        BigDecimal computedDebit = ZERO;
        int returnedCount = 0;
        for (int index = 1; index < lines.length - 1; index++) {
            int recordNumber = index + 1;
            List<String> fields = lex(lines[index], recordNumber);
            if (fields.size() != 13) {
                throw new ProcessorException(
                        "INVALID_FIELD_COUNT",
                        "Event record has the wrong field count",
                        recordNumber,
                        null);
            }
            Event event = parseEvent(
                    fields,
                    recordNumber,
                    fileDate);
            if (!endToEndIds.add(event.endToEndId())
                    || !transactionIds.add(event.transactionId())) {
                throw new ProcessorException(
                        "DUPLICATE_IDENTIFIER",
                        "Type 02 identifier is duplicated in the batch",
                        recordNumber,
                        null);
            }
            if ("C".equals(event.direction())) {
                computedCredit =
                        computedCredit.add(event.amount());
            } else {
                computedDebit =
                        computedDebit.add(event.amount());
            }
            if ("RETURNED".equals(event.status())) {
                returnedCount++;
            }
            events.add(event);
        }

        int declaredCount = parseEventCount(
                trailer.get(1),
                lines.length);
        BigDecimal declaredCredit = parseMoney(
                trailer.get(2),
                false,
                lines.length);
        BigDecimal declaredDebit = parseMoney(
                trailer.get(3),
                false,
                lines.length);
        BigDecimal declaredNet = parseMoney(
                trailer.get(4),
                true,
                lines.length);
        if ("-0.00".equals(trailer.get(4))) {
            throw new ProcessorException(
                    "INVALID_AMOUNT",
                    "Trailer net amount is noncanonical",
                    lines.length,
                    null);
        }
        return new ParsedBatch(
                batchId,
                fileDate,
                List.copyOf(events),
                declaredCount,
                declaredCredit,
                declaredDebit,
                declaredNet,
                computedCredit,
                computedDebit,
                computedCredit.subtract(computedDebit),
                returnedCount);
    }

    static CsvOutput renderCsv(
            ParsedBatch batch,
            String sourceFilename,
            String documentKey) throws ProcessorException {
        if (documentKey == null || documentKey.isBlank()) {
            throw new ProcessorException(
                    "DOCUMENT_TOKEN_KEY_MISSING",
                    "Type 02 document tokenization key is required");
        }
        StringBuilder output =
                new StringBuilder(CSV_HEADER).append('\n');
        for (Event event : batch.events()) {
            BigDecimal signedAmount = "C".equals(event.direction())
                    ? event.amount()
                    : event.amount().negate();
            List<String> fields = List.of(
                    batch.batchId(),
                    sourceFilename,
                    Integer.toString(event.recordNumber()),
                    event.endToEndId(),
                    event.transactionId(),
                    tokenize(event.payerDocument(), documentKey),
                    mask(
                            event.payerDocumentType(),
                            event.payerDocument()),
                    tokenize(event.payeeDocument(), documentKey),
                    mask(
                            event.payeeDocumentType(),
                            event.payeeDocument()),
                    event.timestampLexeme(),
                    money(signedAmount),
                    event.direction(),
                    event.status(),
                    event.returnCode(),
                    event.description());
            for (int index = 0; index < fields.size(); index++) {
                if (index > 0) {
                    output.append(',');
                }
                output.append(csvField(fields.get(index)));
            }
            output.append('\n');
        }
        byte[] bytes =
                output.toString().getBytes(StandardCharsets.UTF_8);
        if (bytes.length > MAX_CSV_BYTES) {
            throw new ProcessorException(
                    "INVALID_TRANSPORT",
                    "Sanitized Type 02 CSV exceeds its contract limit");
        }
        validatePrivacyBoundary(output, batch.events());
        return new CsvOutput(
                bytes,
                batch.events().size(),
                batch.computedCredit(),
                batch.computedDebit(),
                batch.computedNet(),
                batch.returnedCount());
    }

    static void validateSourceControls(
            ParsedBatch batch,
            JsonNode manifest) throws ProcessorException {
        JsonNode controls = manifest.path("source_controls");
        String manifestCredit =
                controls.path("credit_amount").asText();
        String manifestDebit =
                controls.path("debit_amount").asText();
        String manifestNet =
                controls.path("net_amount").asText();
        int manifestCount =
                controls.path("event_count").asInt(-1);
        if (!controls.isObject()
                || !controls.path("currency").isTextual()
                || !"BRL".equals(controls.path("currency").asText())
                || !controls.path("credit_amount").isTextual()
                || !controls.path("debit_amount").isTextual()
                || !controls.path("net_amount").isTextual()
                || !controls.path("event_count").isIntegralNumber()
                || !controls.path("event_count").canConvertToInt()
                || !isCanonicalMoney(manifestCredit, false)
                || !isCanonicalMoney(manifestDebit, false)
                || !isCanonicalMoney(manifestNet, true)
                || "-0.00".equals(manifestNet)
                || manifestCount != batch.declaredCount()
                || !manifestCredit.equals(money(batch.declaredCredit()))
                || !manifestDebit.equals(money(batch.declaredDebit()))
                || !manifestNet.equals(money(batch.declaredNet()))) {
            throw new ProcessorException(
                    "INVALID_MANIFEST",
                    "Type 02 source controls do not match its trailer");
        }
        if (batch.declaredCount() != batch.events().size()) {
            throw sourceControlFailure(
                    "SOURCE_CONTROL_COUNT_MISMATCH",
                    batch);
        }
        if (batch.declaredCredit().compareTo(
                batch.computedCredit()) != 0) {
            throw sourceControlFailure(
                    "SOURCE_CONTROL_CREDIT_MISMATCH",
                    batch);
        }
        if (batch.declaredDebit().compareTo(
                batch.computedDebit()) != 0) {
            throw sourceControlFailure(
                    "SOURCE_CONTROL_DEBIT_MISMATCH",
                    batch);
        }
        if (batch.declaredNet().compareTo(
                batch.computedNet()) != 0) {
            throw sourceControlFailure(
                    "SOURCE_CONTROL_NET_MISMATCH",
                    batch);
        }
    }

    private static SourceDescriptor validateManifest(
            JsonNode manifest,
            String batchId) throws ProcessorException {
        JsonNode fileType = manifest.path("file_type");
        JsonNode sourceFile = manifest.path("source_file");
        String filename = sourceFile.path("name").asText();
        String sha256 = sourceFile.path("sha256").asText();
        long sizeBytes = sourceFile.path("size_bytes").asLong(-1);
        Matcher match = FILENAME_PATTERN.matcher(filename);
        if (!manifest.isObject()
                || !manifest.path("schema_version").isIntegralNumber()
                || manifest.path("schema_version").intValue() != 1
                || !manifest.path("batch_id").isTextual()
                || !batchId.equals(manifest.path("batch_id").asText())
                || !fileType.path("number").isTextual()
                || !"02".equals(fileType.path("number").asText())
                || !fileType.path("code").isTextual()
                || !"PIX_EVENTS01".equals(
                        fileType.path("code").asText())
                || !fileType.path("layout_version").isTextual()
                || !"001".equals(
                        fileType.path("layout_version").asText())
                || !fileType.path("contract_version").isIntegralNumber()
                || fileType.path("contract_version").intValue() != 1
                || !sourceFile.path("name").isTextual()
                || !match.matches()
                || !batchId.equals(match.group(2))
                || !match.group(1).equals(batchId.substring(1, 9))
                || !sourceFile.path("sha256").isTextual()
                || !sha256.matches("[0-9a-f]{64}")
                || !sourceFile.path("size_bytes").isIntegralNumber()
                || !sourceFile.path("size_bytes").canConvertToLong()
                || sizeBytes < 1
                || sizeBytes > MAX_SOURCE_BYTES
                || !sourceFile.path("encoding").isTextual()
                || !"UTF-8".equals(
                        sourceFile.path("encoding").asText())
                || !sourceFile.path("line_ending").isTextual()
                || !"LF".equals(
                        sourceFile.path("line_ending").asText())
                || !sourceFile.path("final_newline").isTextual()
                || !"required".equals(
                        sourceFile.path("final_newline").asText())) {
            throw new ProcessorException(
                    "INVALID_MANIFEST",
                    "Source manifest does not match Type 02");
        }
        return new SourceDescriptor(filename, sha256, sizeBytes);
    }

    private static String decodeTransport(byte[] rawBytes)
            throws ProcessorException {
        if (rawBytes.length == 0
                || rawBytes.length > MAX_SOURCE_BYTES
                || startsWithBom(rawBytes)
                || rawBytes[rawBytes.length - 1] != '\n'
                || (rawBytes.length > 1
                        && rawBytes[rawBytes.length - 2] == '\n')) {
            throw new ProcessorException(
                    "INVALID_TRANSPORT",
                    "Type 02 transport framing is invalid");
        }
        int physicalRecordBytes = 0;
        for (byte value : rawBytes) {
            if (value == '\r') {
                throw new ProcessorException(
                        "INVALID_TRANSPORT",
                        "Type 02 requires LF-only records");
            }
            if (value == '\n') {
                if (physicalRecordBytes == 0
                        || physicalRecordBytes > MAX_RECORD_BYTES) {
                    throw new ProcessorException(
                            "INVALID_TRANSPORT",
                            "Type 02 physical record size is invalid");
                }
                physicalRecordBytes = 0;
            } else {
                physicalRecordBytes++;
            }
        }
        try {
            return StandardCharsets.UTF_8.newDecoder()
                    .onMalformedInput(CodingErrorAction.REPORT)
                    .onUnmappableCharacter(CodingErrorAction.REPORT)
                    .decode(ByteBuffer.wrap(rawBytes))
                    .toString();
        } catch (CharacterCodingException exception) {
            throw new ProcessorException(
                    "INVALID_UTF8",
                    "Type 02 source is not strict UTF-8");
        }
    }

    private static List<String> lex(
            String line,
            int recordNumber) throws ProcessorException {
        List<String> fields = new ArrayList<>();
        StringBuilder field = new StringBuilder();
        for (int index = 0; index < line.length(); index++) {
            char character = line.charAt(index);
            if (character == '\\') {
                if (index + 1 >= line.length()) {
                    throw new ProcessorException(
                            "INVALID_ESCAPE_SEQUENCE",
                            "Type 02 record has a dangling escape",
                            recordNumber,
                            null);
                }
                char escaped = line.charAt(++index);
                if (escaped != '\\' && escaped != '|') {
                    throw new ProcessorException(
                            "INVALID_ESCAPE_SEQUENCE",
                            "Type 02 record has an unknown escape",
                            recordNumber,
                            null);
                }
                field.append(escaped);
            } else if (character == '|') {
                fields.add(field.toString());
                field.setLength(0);
            } else {
                field.append(character);
            }
        }
        fields.add(field.toString());
        return List.copyOf(fields);
    }

    private static Event parseEvent(
            List<String> fields,
            int recordNumber,
            LocalDate fileDate) throws ProcessorException {
        if (!"D".equals(fields.get(0))
                || !END_TO_END_PATTERN.matcher(
                        fields.get(1)).matches()
                || !TRANSACTION_PATTERN.matcher(
                        fields.get(2)).matches()) {
            throw new ProcessorException(
                    "INVALID_RECORD_SEQUENCE",
                    "Type 02 event identity is invalid",
                    recordNumber,
                    null);
        }
        String payerType = fields.get(3);
        String payerDocument = fields.get(4);
        String payeeType = fields.get(5);
        String payeeDocument = fields.get(6);
        if (!validDocument(payerType, payerDocument)
                || !validDocument(payeeType, payeeDocument)) {
            throw new ProcessorException(
                    "INVALID_DOCUMENT",
                    "Type 02 event has an invalid document",
                    recordNumber,
                    null);
        }

        String timestamp = fields.get(7);
        validateTimestamp(timestamp, fileDate, recordNumber);
        BigDecimal amount =
                parseMoney(fields.get(8), false, recordNumber);
        if (amount.compareTo(ZERO) <= 0
                || (!"C".equals(fields.get(9))
                        && !"D".equals(fields.get(9)))) {
            throw new ProcessorException(
                    "INVALID_AMOUNT",
                    "Type 02 event amount or direction is invalid",
                    recordNumber,
                    null);
        }
        String status = fields.get(10);
        String returnCode = fields.get(11);
        if (("SETTLED".equals(status)
                    && !returnCode.isEmpty())
                || ("RETURNED".equals(status)
                    && !RETURN_CODE_PATTERN.matcher(
                            returnCode).matches())
                || (!"SETTLED".equals(status)
                    && !"RETURNED".equals(status))) {
            throw new ProcessorException(
                    "INVALID_STATUS_RETURN_CODE",
                    "Type 02 status and return code do not agree",
                    recordNumber,
                    null);
        }
        String description = fields.get(12);
        validateDescription(
                description,
                payerDocument,
                payeeDocument,
                recordNumber);
        if (containsRestrictedDocument(
                    fields.get(1),
                    payerDocument,
                    payeeDocument)
                || containsRestrictedDocument(
                    fields.get(2),
                    payerDocument,
                    payeeDocument)) {
            throw new ProcessorException(
                    "INVALID_DOCUMENT",
                    "Type 02 retained identifier violates privacy",
                    recordNumber,
                    null);
        }
        return new Event(
                recordNumber,
                fields.get(1),
                fields.get(2),
                payerType,
                payerDocument,
                payeeType,
                payeeDocument,
                timestamp,
                amount,
                fields.get(9),
                status,
                returnCode,
                description);
    }

    private static void validateTimestamp(
            String value,
            LocalDate fileDate,
            int recordNumber) throws ProcessorException {
        if (!TIMESTAMP_PATTERN.matcher(value).matches()
                || value.endsWith("+00:00")
                || value.endsWith("-00:00")) {
            throw new ProcessorException(
                    "INVALID_TIMESTAMP",
                    "Type 02 timestamp is invalid",
                    recordNumber,
                    null);
        }
        try {
            OffsetDateTime parsed =
                    OffsetDateTime.parse(value);
            LocalDate localDate = parsed
                    .atZoneSameInstant(SAO_PAULO)
                    .toLocalDate();
            if (!fileDate.equals(localDate)) {
                throw new DateTimeParseException(
                        "local date mismatch",
                        value,
                        0);
            }
        } catch (DateTimeParseException exception) {
            throw new ProcessorException(
                    "INVALID_TIMESTAMP",
                    "Type 02 timestamp is invalid",
                    recordNumber,
                    null);
        }
    }

    private static void validateDescription(
            String value,
            String payerDocument,
            String payeeDocument,
            int recordNumber) throws ProcessorException {
        int codePoints = value.codePointCount(0, value.length());
        boolean invalid = codePoints < 1
                || codePoints > 80
                || !Normalizer.isNormalized(
                        value,
                        Normalizer.Form.NFC)
                || "=+-@".indexOf(value.charAt(0)) >= 0
                || RESTRICTED_DIGIT_RUN.matcher(value).find()
                || containsRestrictedDocument(
                        value,
                        payerDocument,
                        payeeDocument);
        for (int offset = 0;
                !invalid && offset < value.length();) {
            int codePoint = value.codePointAt(offset);
            int category = Character.getType(codePoint);
            invalid = category == Character.CONTROL
                    || isBidiControl(codePoint);
            offset += Character.charCount(codePoint);
        }
        if (invalid) {
            throw new ProcessorException(
                    "INVALID_DESCRIPTION",
                    "Type 02 description violates content policy",
                    recordNumber,
                    null);
        }
    }

    private static boolean isBidiControl(int codePoint) {
        return codePoint == 0x061c
                || codePoint == 0x200e
                || codePoint == 0x200f
                || codePoint >= 0x202a && codePoint <= 0x202e
                || codePoint >= 0x2066 && codePoint <= 0x2069;
    }

    private static boolean validDocument(
            String documentType,
            String value) {
        if ("CPF".equals(documentType)) {
            return validCpf(value);
        }
        if ("CNPJ".equals(documentType)) {
            return validCnpj(value);
        }
        return false;
    }

    private static boolean validCpf(String value) {
        if (!asciiDigits(value, 11)
                || allDigitsEqual(value)) {
            return false;
        }
        int first = mod11Digit(
                value,
                9,
                new int[]{10, 9, 8, 7, 6, 5, 4, 3, 2});
        int second = mod11Digit(
                value.substring(0, 9)
                        + first,
                10,
                new int[]{11, 10, 9, 8, 7, 6, 5, 4, 3, 2});
        return value.charAt(9) - '0' == first
                && value.charAt(10) - '0' == second;
    }

    private static boolean validCnpj(String value) {
        if (!asciiDigits(value, 14)
                || allDigitsEqual(value)) {
            return false;
        }
        int first = mod11Digit(
                value,
                12,
                new int[]{5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2});
        int second = mod11Digit(
                value.substring(0, 12)
                        + first,
                13,
                new int[]{6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2});
        return value.charAt(12) - '0' == first
                && value.charAt(13) - '0' == second;
    }

    private static int mod11Digit(
            String value,
            int length,
            int[] weights) {
        int sum = 0;
        for (int index = 0; index < length; index++) {
            sum += (value.charAt(index) - '0') * weights[index];
        }
        int remainder = sum % 11;
        return remainder < 2 ? 0 : 11 - remainder;
    }

    private static boolean asciiDigits(
            String value,
            int length) {
        if (value.length() != length) {
            return false;
        }
        for (int index = 0; index < value.length(); index++) {
            if (value.charAt(index) < '0'
                    || value.charAt(index) > '9') {
                return false;
            }
        }
        return true;
    }

    private static boolean allDigitsEqual(String value) {
        for (int index = 1; index < value.length(); index++) {
            if (value.charAt(index) != value.charAt(0)) {
                return false;
            }
        }
        return true;
    }

    private static int parseEventCount(
            String value,
            int recordNumber) throws ProcessorException {
        try {
            if (!value.matches("[0-9]{1,5}")) {
                throw new NumberFormatException("invalid unsigned integer");
            }
            int count = Integer.parseInt(value);
            if (count < 1 || count > MAX_EVENTS) {
                throw new NumberFormatException("outside limit");
            }
            return count;
        } catch (NumberFormatException exception) {
            throw new ProcessorException(
                    "SOURCE_CONTROL_COUNT_MISMATCH",
                    "Type 02 trailer event count is invalid",
                    recordNumber,
                    null);
        }
    }

    private static BigDecimal parseMoney(
            String value,
            boolean signed,
            int recordNumber) throws ProcessorException {
        if (!isCanonicalMoney(value, signed)) {
            throw new ProcessorException(
                    "INVALID_AMOUNT",
                    "Type 02 amount is noncanonical",
                    recordNumber,
                    null);
        }
        return new BigDecimal(value);
    }

    private static boolean isCanonicalMoney(
            String value,
            boolean signed) {
        return (signed
                ? SIGNED_MONEY_PATTERN
                : UNSIGNED_MONEY_PATTERN)
                .matcher(value)
                .matches();
    }

    private static LocalDate parseFileDate(String value)
            throws ProcessorException {
        try {
            return LocalDate.parse(
                    value,
                    FILE_DATE_FORMATTER);
        } catch (DateTimeParseException exception) {
            throw new ProcessorException(
                    "INVALID_RECORD_SEQUENCE",
                    "Type 02 header date is invalid",
                    1,
                    null);
        }
    }

    private static ProcessorException sourceControlFailure(
            String code,
            ParsedBatch batch) {
        return ProcessorException.type02SourceControlMismatch(
                code,
                batch.declaredCount(),
                money(batch.declaredCredit()),
                money(batch.declaredDebit()),
                money(batch.declaredNet()),
                batch.events().size(),
                money(batch.computedCredit()),
                money(batch.computedDebit()),
                money(batch.computedNet()));
    }

    private static String tokenize(
            String document,
            String key) throws ProcessorException {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(
                    key.getBytes(StandardCharsets.UTF_8),
                    "HmacSHA256"));
            byte[] digest = mac.doFinal(
                    document.getBytes(StandardCharsets.US_ASCII));
            return "doc_" + java.util.HexFormat.of()
                    .formatHex(digest)
                    .substring(0, 24);
        } catch (GeneralSecurityException exception) {
            throw new ProcessorException(
                    "DOCUMENT_TOKENIZATION_ERROR",
                    "Cannot tokenize a protected Type 02 field",
                    exception);
        }
    }

    private static String mask(
            String documentType,
            String document) {
        String stars = "CPF".equals(documentType)
                ? "*******"
                : "**********";
        return stars + document.substring(
                document.length() - 4);
    }

    private static String csvField(String value) {
        if (value.indexOf(',') >= 0
                || value.indexOf('"') >= 0
                || value.indexOf('\n') >= 0
                || value.indexOf('\r') >= 0) {
            return "\"" + value.replace("\"", "\"\"") + "\"";
        }
        return value;
    }

    private static void validatePrivacyBoundary(
            CharSequence csv,
            List<Event> events) throws ProcessorException {
        for (Event event : events) {
            if (containsRestrictedDocument(
                    csv,
                    event.payerDocument(),
                    event.payeeDocument())) {
                throw new ProcessorException(
                        "PRIVACY_BOUNDARY_VIOLATION",
                        "Sanitized Type 02 CSV contains a restricted document",
                        event.recordNumber(),
                        null);
            }
        }
    }

    private static boolean containsRestrictedDocument(
            CharSequence value,
            String payerDocument,
            String payeeDocument) {
        String text = value.toString();
        return text.contains(payerDocument)
                || text.contains(payeeDocument);
    }

    private static Map<String, Object> sanitizedManifest(
            ProcessingContext context,
            SourceDescriptor source,
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
                "code", "PIX_EVENTS01",
                "contract_version", 1,
                "layout_version", "001",
                "number", "02");
        Map<String, Object> lineage = Map.of(
                "manifest_sha256",
                ArtifactIO.sha256(context.sourceManifestBytes()),
                "raw_file", source.filename(),
                "raw_sha256", source.sha256());
        Map<String, Object> controls = Map.of(
                "credit_amount", money(output.creditAmount()),
                "currency", "BRL",
                "debit_amount", money(output.debitAmount()),
                "net_amount", money(output.netAmount()),
                "returned_count", output.returnedCount(),
                "row_count", output.rowCount());
        return Map.of(
                "batch_id", context.batchId(),
                "csv_file", csvFile,
                "file_type", fileType,
                "schema_version", 1,
                "source_lineage", lineage,
                "stage_controls", controls);
    }

    private static String money(BigDecimal value) {
        return value.setScale(2).toPlainString();
    }

    private static boolean startsWithBom(byte[] value) {
        return value.length >= 3
                && (value[0] & 0xff) == 0xef
                && (value[1] & 0xff) == 0xbb
                && (value[2] & 0xff) == 0xbf;
    }

    record SourceDescriptor(
            String filename,
            String sha256,
            long sizeBytes) {
    }

    record Event(
            int recordNumber,
            String endToEndId,
            String transactionId,
            String payerDocumentType,
            String payerDocument,
            String payeeDocumentType,
            String payeeDocument,
            String timestampLexeme,
            BigDecimal amount,
            String direction,
            String status,
            String returnCode,
            String description) {
    }

    record ParsedBatch(
            String batchId,
            LocalDate fileDate,
            List<Event> events,
            int declaredCount,
            BigDecimal declaredCredit,
            BigDecimal declaredDebit,
            BigDecimal declaredNet,
            BigDecimal computedCredit,
            BigDecimal computedDebit,
            BigDecimal computedNet,
            int returnedCount) {
    }

    record CsvOutput(
            byte[] bytes,
            int rowCount,
            BigDecimal creditAmount,
            BigDecimal debitAmount,
            BigDecimal netAmount,
            int returnedCount) {
    }
}

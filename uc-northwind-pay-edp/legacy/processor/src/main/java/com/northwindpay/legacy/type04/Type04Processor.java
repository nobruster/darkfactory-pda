package com.northwindpay.legacy.type04;

import com.fasterxml.jackson.databind.JsonNode;
import com.northwindpay.legacy.core.ArtifactIO;
import com.northwindpay.legacy.core.BatchProcessor;
import com.northwindpay.legacy.core.Configuration;
import com.northwindpay.legacy.core.DiagnosticPrivacy;
import com.northwindpay.legacy.core.ProcessingContext;
import com.northwindpay.legacy.core.ProcessorException;
import com.northwindpay.legacy.core.ProcessorResult;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.time.DateTimeException;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.time.format.ResolverStyle;
import java.time.zone.ZoneRules;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.HexFormat;
import java.util.Iterator;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Contract-faithful Type 04 TED transfer-settlement converter.
 *
 * <p>The parser treats transport bytes, heterogeneous record lengths,
 * status-selected {@code D}/{@code D R} branches, São Paulo local timestamps,
 * exact signed decimals, and privacy publication as separate fail-closed
 * boundaries. It never publishes a partial sanitized bundle.
 */
public final class Type04Processor implements BatchProcessor {
    private static final int HEADER_BYTES = 56;
    private static final int TRANSFER_BYTES = 162;
    private static final int RETURN_BYTES = 91;
    private static final int TRAILER_BYTES = 82;
    private static final int MIN_SOURCE_BYTES = 306;
    private static final int MAX_SOURCE_BYTES = 2_570_142;
    private static final int MAX_PHYSICAL_RECORDS = 20_002;
    private static final int MAX_TRANSFERS = 10_000;
    private static final int MAX_RETURNS = 10_000;
    private static final int MAX_MOVEMENTS = 20_000;
    private static final int MAX_CSV_BYTES = 10_000_000;
    private static final BigDecimal ZERO = new BigDecimal("0.00");
    private static final ZoneId SAO_PAULO =
            ZoneId.of("America/Sao_Paulo");
    private static final DateTimeFormatter SOURCE_DATE =
            DateTimeFormatter.ofPattern("uuuuMMdd", Locale.ROOT)
                    .withResolverStyle(ResolverStyle.STRICT);
    private static final DateTimeFormatter SOURCE_TIME =
            DateTimeFormatter.ofPattern("HHmmss", Locale.ROOT)
                    .withResolverStyle(ResolverStyle.STRICT);
    private static final DateTimeFormatter OUTPUT_TIMESTAMP =
            DateTimeFormatter.ofPattern(
                    "uuuu-MM-dd'T'HH:mm:ssxxx",
                    Locale.ROOT);
    private static final Pattern BATCH_PATTERN =
            Pattern.compile("B[0-9]{15}");
    private static final Pattern FILENAME_PATTERN = Pattern.compile(
            "NW_TED_SETTLEMENT_([0-9]{8})_(B[0-9]{15})\\.dat");
    private static final Pattern SAFE_IDENTIFIER =
            Pattern.compile("[A-Z][A-Z0-9]{15}");
    private static final Pattern PURPOSE_CODE =
            Pattern.compile("[A-Z][A-Z0-9_]{1,9}");
    private static final Pattern REASON_CODE =
            Pattern.compile("[A-Z][A-Z0-9]{4}");
    private static final Pattern BENEFICIARY_NAME =
            Pattern.compile("[A-Z][A-Z0-9 .&/-]{0,22}");
    private static final Pattern RETURN_REASON_TEXT =
            Pattern.compile("[A-Z][A-Z0-9 .&/-]{0,23}");
    private static final Pattern CANONICAL_UNSIGNED_MONEY =
            Pattern.compile("(?:0|[1-9][0-9]{0,15})\\.[0-9]{2}");
    private static final Pattern CANONICAL_RETURNED_MONEY =
            Pattern.compile(
                    "(?:0\\.00|-(?:0\\.(?!00$)[0-9]{2}|"
                            + "[1-9][0-9]{0,15}\\.[0-9]{2}))");
    private static final Set<String> MANIFEST_FIELDS = Set.of(
            "batch_id",
            "file_type",
            "schema_version",
            "source_controls",
            "source_file");
    private static final Set<String> FILE_TYPE_FIELDS = Set.of(
            "code",
            "contract_version",
            "layout_version",
            "number");
    private static final Set<String> SOURCE_FILE_FIELDS = Set.of(
            "encoding",
            "final_newline",
            "line_ending",
            "name",
            "sha256",
            "size_bytes");
    private static final Set<String> SOURCE_CONTROL_FIELDS = Set.of(
            "currency",
            "gross_amount",
            "net_amount",
            "return_amount",
            "return_count",
            "transfer_count");
    private static final String CSV_HEADER = String.join(",",
            "batch_id",
            "source_file",
            "source_record_number",
            "movement_id",
            "original_transfer_id",
            "movement_kind",
            "movement_ts",
            "amount_brl",
            "payer_account_token",
            "payer_tax_id_masked",
            "beneficiary_account_token",
            "beneficiary_tax_id_masked",
            "beneficiary_ispb",
            "purpose_code",
            "status_code",
            "return_reason_code");

    @Override
    public String typeNumber() {
        return "04";
    }

    @Override
    public String typeCode() {
        return "TED_SETTLE04";
    }

    @Override
    public String layoutVersion() {
        return "001";
    }

    /**
     * Validates, sanitizes, and atomically publishes one Type 04 source.
     *
     * @param context integrity-checked source and publication boundary
     * @return aggregate-only success evidence
     * @throws ProcessorException when any contract boundary fails
     */
    @Override
    public ProcessorResult process(ProcessingContext context)
            throws ProcessorException {
        byte[] rawBytes = context.sourceArtifact().bytes();
        DiagnosticPrivacy privacy = diagnosticPrivacyForRaw(rawBytes);
        try {
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
                        "Acquired source does not match Type 04 metadata");
            }
            TokenKey key = validateTokenKey(context.configuration());
            ParsedBatch parsed = parseRaw(
                    rawBytes,
                    source.filename(),
                    context.batchId());
            validateSourceControls(parsed, context.sourceManifest());
            CsvOutput csv = renderCsv(
                    parsed,
                    source.filename(),
                    key);
            String csvFilename = source.filename().substring(
                    0,
                    source.filename().length() - ".dat".length()) + ".csv";
            String csvSha256 = ArtifactIO.sha256(csv.bytes());
            ArtifactIO.PublishedCsv published =
                    ArtifactIO.publishSanitized(
                            context,
                            csvFilename,
                            csv.bytes(),
                            sanitizedManifest(
                                    context,
                                    source,
                                    csvFilename,
                                    csvSha256,
                                    csv));
            return ProcessorResult.type04Succeeded(
                    context.batchId(),
                    published.filename(),
                    published.sha256(),
                    csv.rowCount(),
                    csv.transferCount(),
                    csv.returnCount(),
                    money(csv.grossAmount()),
                    money(csv.returnAmount()),
                    money(csv.netAmount()));
        } catch (ProcessorException exception) {
            throw exception.withDiagnosticPrivacy(privacy);
        }
    }

    /**
     * Parses every non-control rule in the declared global precedence.
     *
     * <p>Trailer reconciliation is deliberately separate so the manifest can
     * first be proven equal to the source declarations.
     */
    static ParsedBatch parseRaw(
            byte[] rawBytes,
            String sourceFilename,
            String expectedBatchId) throws ProcessorException {
        DiagnosticPrivacy privacy = diagnosticPrivacyForRaw(rawBytes);
        try {
            List<String> records = decodeRecords(rawBytes);
            List<MovementSpan> spans =
                    validateConditionalGrammar(records);
            validateStaticFields(
                    records,
                    sourceFilename,
                    expectedBatchId);
            ParsedBatch parsed = parseLexicalFields(
                    records,
                    spans,
                    sourceFilename,
                    expectedBatchId);
            validateDocuments(parsed.transfers());
            validateSafeIdentifiers(parsed);
            validateReturnLinkage(parsed.transfers());
            validateUniquenessAndTimestamps(parsed.transfers());
            return parsed;
        } catch (ProcessorException exception) {
            throw exception.withDiagnosticPrivacy(privacy);
        }
    }

    /**
     * Validates manifest-to-trailer equality, then computed controls in their
     * contract order.
     */
    static void validateSourceControls(
            ParsedBatch batch,
            JsonNode manifest) throws ProcessorException {
        JsonNode controls = manifest.path("source_controls");
        if (!validControlObject(controls)) {
            throw invalidManifest();
        }
        if (controls.path("transfer_count").intValue()
                    != batch.declaredTransferCount()
                || controls.path("return_count").intValue()
                    != batch.declaredReturnCount()
                || !controls.path("gross_amount").asText().equals(
                        money(batch.declaredGrossAmount()))
                || !controls.path("return_amount").asText().equals(
                        money(batch.declaredReturnAmount()))
                || !controls.path("net_amount").asText().equals(
                        money(batch.declaredNetAmount()))) {
            throw invalidManifest();
        }

        if (batch.declaredTransferCount()
                != batch.computedTransferCount()) {
            throw sourceControlFailure(
                    "SOURCE_CONTROL_TRANSFER_COUNT_MISMATCH",
                    batch);
        }
        if (batch.declaredReturnCount()
                != batch.computedReturnCount()) {
            throw sourceControlFailure(
                    "SOURCE_CONTROL_RETURN_COUNT_MISMATCH",
                    batch);
        }
        if (batch.declaredGrossAmount().compareTo(
                batch.computedGrossAmount()) != 0) {
            throw sourceControlFailure(
                    "SOURCE_CONTROL_GROSS_MISMATCH",
                    batch);
        }
        if (batch.declaredReturnAmount().compareTo(
                batch.computedReturnAmount()) != 0) {
            throw sourceControlFailure(
                    "SOURCE_CONTROL_RETURNED_MISMATCH",
                    batch);
        }
        if (batch.declaredNetAmount().compareTo(
                batch.computedNetAmount()) != 0) {
            throw sourceControlFailure(
                    "SOURCE_CONTROL_NET_MISMATCH",
                    batch);
        }
    }

    /**
     * Renders exact UTF-8/LF CSV and scans the complete candidate output for
     * every prohibited raw value before any file is written.
     */
    static CsvOutput renderCsv(
            ParsedBatch batch,
            String sourceFilename,
            TokenKey tokenKey) throws ProcessorException {
        StringBuilder rendered =
                new StringBuilder(CSV_HEADER).append('\n');
        for (Transfer transfer : batch.transfers()) {
            String payerToken = token(
                    tokenKey.value(),
                    transfer.payerAccountInput());
            String beneficiaryToken = token(
                    tokenKey.value(),
                    transfer.beneficiaryAccountInput());
            String payerMask = maskTaxId(
                    transfer.payerTaxId(),
                    transfer.payerPartyType());
            String beneficiaryMask = maskTaxId(
                    transfer.beneficiaryTaxId(),
                    transfer.beneficiaryPartyType());
            appendCsvRow(rendered, List.of(
                    batch.batchId(),
                    sourceFilename,
                    Integer.toString(transfer.recordNumber()),
                    transfer.transferId(),
                    "",
                    "TRANSFER",
                    OUTPUT_TIMESTAMP.format(transfer.timestamp()),
                    money(transfer.amount()),
                    payerToken,
                    payerMask,
                    beneficiaryToken,
                    beneficiaryMask,
                    transfer.beneficiaryIspb(),
                    transfer.purposeCode(),
                    transfer.statusCode(),
                    ""));
            ReturnMovement returned = transfer.returnMovement();
            if (returned != null) {
                appendCsvRow(rendered, List.of(
                        batch.batchId(),
                        sourceFilename,
                        Integer.toString(returned.recordNumber()),
                        returned.returnId(),
                        returned.originalTransferId(),
                        "RETURN",
                        OUTPUT_TIMESTAMP.format(returned.timestamp()),
                        money(returned.amount().negate()),
                        payerToken,
                        payerMask,
                        beneficiaryToken,
                        beneficiaryMask,
                        transfer.beneficiaryIspb(),
                        transfer.purposeCode(),
                        transfer.statusCode(),
                        returned.reasonCode()));
            }
        }
        byte[] bytes = rendered.toString()
                .getBytes(StandardCharsets.UTF_8);
        if (bytes.length > MAX_CSV_BYTES) {
            throw new ProcessorException(
                    "INVALID_TRANSPORT",
                    "Sanitized Type 04 CSV exceeds its contract limit");
        }
        validatePrivacyBoundary(rendered, batch.transfers());
        return new CsvOutput(
                bytes,
                batch.computedTransferCount()
                        + batch.computedReturnCount(),
                batch.computedTransferCount(),
                batch.computedReturnCount(),
                batch.computedGrossAmount(),
                batch.computedReturnAmount(),
                batch.computedNetAmount());
    }

    private static SourceDescriptor validateManifest(
            JsonNode manifest,
            String batchId) throws ProcessorException {
        JsonNode fileType = manifest.path("file_type");
        JsonNode sourceFile = manifest.path("source_file");
        String filename = sourceFile.path("name").asText();
        String sha256 = sourceFile.path("sha256").asText();
        long sizeBytes = sourceFile.path("size_bytes").asLong(-1);
        Matcher filenameMatch = FILENAME_PATTERN.matcher(filename);
        if (!hasExactFields(manifest, MANIFEST_FIELDS)
                || !manifest.path("schema_version").isIntegralNumber()
                || !manifest.path("schema_version").canConvertToInt()
                || manifest.path("schema_version").intValue() != 1
                || !manifest.path("batch_id").isTextual()
                || !batchId.equals(manifest.path("batch_id").asText())
                || !BATCH_PATTERN.matcher(batchId).matches()
                || !hasExactFields(fileType, FILE_TYPE_FIELDS)
                || !fileType.path("number").isTextual()
                || !"04".equals(fileType.path("number").asText())
                || !fileType.path("code").isTextual()
                || !"TED_SETTLE04".equals(
                        fileType.path("code").asText())
                || !fileType.path("layout_version").isTextual()
                || !"001".equals(
                        fileType.path("layout_version").asText())
                || !fileType.path("contract_version").isIntegralNumber()
                || !fileType.path("contract_version").canConvertToInt()
                || fileType.path("contract_version").intValue() != 1
                || !hasExactFields(sourceFile, SOURCE_FILE_FIELDS)
                || !sourceFile.path("name").isTextual()
                || !filenameMatch.matches()
                || !batchId.equals(filenameMatch.group(2))
                || !sourceFile.path("sha256").isTextual()
                || !sha256.matches("[0-9a-f]{64}")
                || !sourceFile.path("size_bytes").isIntegralNumber()
                || !sourceFile.path("size_bytes").canConvertToLong()
                || sizeBytes < MIN_SOURCE_BYTES
                || sizeBytes > MAX_SOURCE_BYTES
                || !sourceFile.path("encoding").isTextual()
                || !"US-ASCII".equals(
                        sourceFile.path("encoding").asText())
                || !sourceFile.path("line_ending").isTextual()
                || !"CRLF".equals(
                        sourceFile.path("line_ending").asText())
                || !sourceFile.path("final_newline").isTextual()
                || !"required".equals(
                        sourceFile.path("final_newline").asText())
                || !validControlObject(
                        manifest.path("source_controls"))) {
            throw invalidManifest();
        }
        return new SourceDescriptor(filename, sha256, sizeBytes);
    }

    private static TokenKey validateTokenKey(
            Configuration configuration) throws ProcessorException {
        String tedKey = configuration.tedAccountTokenKey();
        if (tedKey == null || tedKey.isBlank()) {
            throw new ProcessorException(
                    "TOKENIZATION_KEY_MISSING",
                    "Type 04 requires its TED account tokenization key");
        }
        List<String> otherDomains = List.of(
                nullToEmpty(configuration.tokenizationKey()),
                nullToEmpty(configuration.documentTokenKey()),
                nullToEmpty(configuration.paymentReferenceKey()),
                nullToEmpty(configuration.partyTokenKey()),
                nullToEmpty(configuration.accountTokenKey()));
        for (String otherKey : otherDomains) {
            if (!otherKey.isBlank() && tedKey.equals(otherKey)) {
                throw new ProcessorException(
                        "TOKENIZATION_KEY_REUSE",
                        "Type 04 tokenization key is not independent");
            }
        }
        return new TokenKey(tedKey);
    }

    private static List<String> decodeRecords(byte[] rawBytes)
            throws ProcessorException {
        if (rawBytes == null
                || rawBytes.length < MIN_SOURCE_BYTES
                || rawBytes.length > MAX_SOURCE_BYTES) {
            throw new ProcessorException(
                    "INVALID_SOURCE_SIZE",
                    "Type 04 source size is outside contract bounds");
        }
        for (byte value : rawBytes) {
            if ((value & 0xff) > 0x7f) {
                throw new ProcessorException(
                        "INVALID_ASCII",
                        "Type 04 source is not strict US-ASCII");
            }
        }
        if (rawBytes.length < 2
                || rawBytes[rawBytes.length - 2] != '\r'
                || rawBytes[rawBytes.length - 1] != '\n') {
            throw new ProcessorException(
                    "INVALID_TRANSPORT",
                    "Type 04 source requires a final CRLF");
        }
        int recordStart = 0;
        for (int index = 0; index < rawBytes.length; index++) {
            byte value = rawBytes[index];
            if (value == '\r') {
                if (index + 1 >= rawBytes.length
                        || rawBytes[index + 1] != '\n') {
                    throw new ProcessorException(
                            "INVALID_TRANSPORT",
                            "Type 04 source contains a bare CR");
                }
                if (index == recordStart) {
                    throw new ProcessorException(
                            "INVALID_TRANSPORT",
                            "Type 04 source contains a blank record");
                }
            } else if (value == '\n'
                    && (index == 0 || rawBytes[index - 1] != '\r')) {
                throw new ProcessorException(
                        "INVALID_TRANSPORT",
                        "Type 04 source contains a bare LF");
            } else if (value == '\n') {
                recordStart = index + 1;
            }
        }
        String text = new String(rawBytes, StandardCharsets.US_ASCII);
        String[] split = text.substring(0, text.length() - 2)
                .split("\\r\\n", -1);
        for (int index = 0; index < split.length; index++) {
            String record = split[index];
            int expectedLength = switch (record.charAt(0)) {
                case 'H' -> HEADER_BYTES;
                case 'D' -> TRANSFER_BYTES;
                case 'R' -> RETURN_BYTES;
                case 'T' -> TRAILER_BYTES;
                default -> throw new ProcessorException(
                        "INVALID_RECORD_SEQUENCE",
                        "Type 04 record discriminator is unknown",
                        index + 1,
                        null);
            };
            if (record.length() != expectedLength) {
                throw new ProcessorException(
                        "INVALID_RECORD_LENGTH",
                        "Type 04 record has the wrong variant length",
                        index + 1,
                        null);
            }
        }
        if (split.length < 3
                || split.length > MAX_PHYSICAL_RECORDS) {
            throw new ProcessorException(
                    "INVALID_RECORD_SEQUENCE",
                    "Type 04 physical record count is outside bounds");
        }
        return List.of(split);
    }

    private static List<MovementSpan> validateConditionalGrammar(
            List<String> records) throws ProcessorException {
        if (records.getFirst().charAt(0) != 'H'
                || records.getLast().charAt(0) != 'T') {
            throw new ProcessorException(
                    "INVALID_RECORD_SEQUENCE",
                    "Type 04 header or trailer is misplaced");
        }
        List<MovementSpan> spans = new ArrayList<>();
        int returns = 0;
        int index = 1;
        int last = records.size() - 1;
        while (index < last) {
            if (records.get(index).charAt(0) != 'D') {
                throw new ProcessorException(
                        "INVALID_RECORD_SEQUENCE",
                        "Type 04 transfer is misplaced",
                        index + 1,
                        null);
            }
            String rawStatus = records.get(index).substring(137, 139);
            boolean hasReturn = index + 1 < last
                    && records.get(index + 1).charAt(0) == 'R';
            boolean hasSecondReturn = hasReturn
                    && index + 2 < last
                    && records.get(index + 2).charAt(0) == 'R';
            if ("RT".equals(rawStatus)) {
                if (!hasReturn || hasSecondReturn) {
                    throw new ProcessorException(
                            "RETURN_LINK_MISMATCH",
                            "Type 04 RT branch requires one return",
                            index + 1,
                            null);
                }
            } else if ("OK".equals(rawStatus) && hasReturn) {
                throw new ProcessorException(
                        "RETURN_LINK_MISMATCH",
                        "Type 04 OK branch forbids a return",
                        index + 1,
                        null);
            }
            Integer returnIndex = hasReturn ? index + 1 : null;
            spans.add(new MovementSpan(index, returnIndex));
            if (returnIndex != null) {
                returns++;
            }
            index += returnIndex == null ? 1 : 2;
        }
        if (spans.isEmpty()) {
            throw new ProcessorException(
                    "INVALID_RECORD_SEQUENCE",
                    "Type 04 requires at least one transfer");
        }
        if (spans.size() > MAX_TRANSFERS
                || returns > MAX_RETURNS
                || spans.size() + returns > MAX_MOVEMENTS) {
            throw new ProcessorException(
                    "INVALID_SOURCE_SIZE",
                    "Type 04 movement count exceeds its contract");
        }
        return List.copyOf(spans);
    }

    private static void validateStaticFields(
            List<String> records,
            String sourceFilename,
            String expectedBatchId) throws ProcessorException {
        Matcher filenameMatch =
                FILENAME_PATTERN.matcher(sourceFilename);
        if (!filenameMatch.matches()) {
            throw invalidField(1);
        }
        String header = records.getFirst();
        String fileDate = header.substring(1, 9);
        String settlementDate = header.substring(40, 48);
        parseDate(fileDate, 1);
        parseDate(settlementDate, 1);
        if (!header.substring(25, 37).equals("TED_SETTLE04")
                || !header.substring(37, 40).equals("001")
                || !fileDate.equals(settlementDate)
                || !fileDate.equals(filenameMatch.group(1))
                || !header.substring(9, 25).equals(expectedBatchId)
                || !header.substring(9, 25).equals(
                        filenameMatch.group(2))) {
            throw invalidField(1);
        }
        for (int index = 1; index < records.size() - 1; index++) {
            String record = records.get(index);
            if (record.charAt(0) == 'D') {
                OffsetDateTime timestamp = parseTimestamp(
                        record.substring(35, 43),
                        record.substring(43, 49),
                        index + 1);
                rightTildeUnpad(record, 127, 137, index + 1);
                rightTildeUnpad(record, 139, 162, index + 1);
                if (record.charAt(17) != '+'
                        || !"BRL".equals(record.substring(32, 35))) {
                    throw invalidField(index + 1);
                }
                if (!timestamp.toLocalDate().equals(
                        parseDate(settlementDate, 1))) {
                    throw invalidTimestamp(index + 1);
                }
            } else {
                parseTimestamp(
                        record.substring(48, 56),
                        record.substring(56, 62),
                        index + 1);
                rightTildeUnpad(record, 67, 91, index + 1);
                if (record.charAt(33) != '-') {
                    throw invalidField(index + 1);
                }
            }
        }
        String trailer = records.getLast();
        parseDate(trailer.substring(1, 9), records.size());
        if (!trailer.substring(1, 9).equals(fileDate)
                || trailer.charAt(21) != '+'
                || (trailer.charAt(36) != '+'
                    && trailer.charAt(36) != '-')
                || trailer.charAt(51) != '+'
                || !trailer.substring(66, 82).equals(
                        expectedBatchId)) {
            throw invalidField(records.size());
        }
    }

    private static ParsedBatch parseLexicalFields(
            List<String> records,
            List<MovementSpan> spans,
            String sourceFilename,
            String expectedBatchId) throws ProcessorException {
        String header = records.getFirst();
        if (!asciiDigits(header.substring(48, 56))) {
            throw invalidField(1);
        }
        List<Transfer> transfers = new ArrayList<>();
        for (MovementSpan span : spans) {
            int transferNumber = span.transferIndex() + 1;
            String transfer = records.get(span.transferIndex());
            String payerIspb = transfer.substring(49, 57);
            String payerBranch = transfer.substring(57, 61);
            String payerAccount = transfer.substring(61, 73);
            String payerTaxId = transfer.substring(73, 87);
            String beneficiaryIspb = transfer.substring(88, 96);
            String beneficiaryBranch = transfer.substring(96, 100);
            String beneficiaryAccount = transfer.substring(100, 112);
            String beneficiaryTaxId = transfer.substring(112, 126);
            if (!asciiDigits(transfer.substring(18, 32))
                    || !asciiDigits(payerIspb)
                    || !asciiDigits(payerBranch)
                    || !asciiDigits(payerAccount)
                    || !asciiDigits(payerTaxId)
                    || !asciiDigits(beneficiaryIspb)
                    || !asciiDigits(beneficiaryBranch)
                    || !asciiDigits(beneficiaryAccount)
                    || !asciiDigits(beneficiaryTaxId)
                    || (transfer.charAt(87) != 'F'
                        && transfer.charAt(87) != 'J')
                    || (transfer.charAt(126) != 'F'
                        && transfer.charAt(126) != 'J')
                    || (!"OK".equals(transfer.substring(137, 139))
                        && !"RT".equals(
                                transfer.substring(137, 139)))) {
                throw invalidField(transferNumber);
            }
            BigDecimal amount = parseImpliedMoney(
                    transfer.substring(18, 32),
                    transferNumber);
            if (amount.compareTo(ZERO) <= 0) {
                throw invalidField(transferNumber);
            }
            ReturnMovement returned = null;
            if (span.returnIndex() != null) {
                int returnNumber = span.returnIndex() + 1;
                String returnRecord = records.get(span.returnIndex());
                if (!asciiDigits(returnRecord.substring(34, 48))) {
                    throw invalidField(returnNumber);
                }
                BigDecimal returnAmount = parseImpliedMoney(
                        returnRecord.substring(34, 48),
                        returnNumber);
                if (returnAmount.compareTo(ZERO) <= 0) {
                    throw invalidField(returnNumber);
                }
                returned = new ReturnMovement(
                        returnNumber,
                        returnRecord.substring(1, 17),
                        returnRecord.substring(17, 33),
                        returnAmount,
                        parseTimestamp(
                                returnRecord.substring(48, 56),
                                returnRecord.substring(56, 62),
                                returnNumber),
                        returnRecord.substring(62, 67),
                        rightTildeUnpad(
                                returnRecord,
                                67,
                                91,
                                returnNumber));
            }
            transfers.add(new Transfer(
                    transferNumber,
                    transfer.substring(1, 17),
                    amount,
                    parseTimestamp(
                            transfer.substring(35, 43),
                            transfer.substring(43, 49),
                            transferNumber),
                    payerIspb,
                    payerBranch,
                    payerAccount,
                    payerTaxId,
                    transfer.charAt(87),
                    beneficiaryIspb,
                    beneficiaryBranch,
                    beneficiaryAccount,
                    beneficiaryTaxId,
                    transfer.charAt(126),
                    rightTildeUnpad(
                            transfer,
                            127,
                            137,
                            transferNumber),
                    transfer.substring(137, 139),
                    rightTildeUnpad(
                            transfer,
                            139,
                            162,
                            transferNumber),
                    returned));
        }

        String trailer = records.getLast();
        int trailerNumber = records.size();
        for (String numeric : List.of(
                trailer.substring(9, 15),
                trailer.substring(15, 21),
                trailer.substring(22, 36),
                trailer.substring(37, 51),
                trailer.substring(52, 66))) {
            if (!asciiDigits(numeric)) {
                throw invalidField(trailerNumber);
            }
        }
        int declaredTransferCount = parseBoundedInteger(
                trailer.substring(9, 15),
                1,
                MAX_TRANSFERS,
                trailerNumber);
        int declaredReturnCount = parseBoundedInteger(
                trailer.substring(15, 21),
                0,
                MAX_RETURNS,
                trailerNumber);
        BigDecimal declaredGross = parseImpliedMoney(
                trailer.substring(22, 36),
                trailerNumber);
        BigDecimal returnedMagnitude = parseImpliedMoney(
                trailer.substring(37, 51),
                trailerNumber);
        BigDecimal declaredNet = parseImpliedMoney(
                trailer.substring(52, 66),
                trailerNumber);
        if (declaredReturnCount > declaredTransferCount
                || declaredGross.compareTo(ZERO) <= 0
                || (declaredReturnCount == 0
                    && (trailer.charAt(36) != '+'
                        || returnedMagnitude.compareTo(ZERO) != 0))
                || (declaredReturnCount > 0
                    && (trailer.charAt(36) != '-'
                        || returnedMagnitude.compareTo(ZERO) <= 0))) {
            throw invalidField(trailerNumber);
        }
        BigDecimal declaredReturn = declaredReturnCount == 0
                ? ZERO
                : returnedMagnitude.negate();
        BigDecimal computedGross = ZERO;
        BigDecimal computedReturn = ZERO;
        int computedReturns = 0;
        for (Transfer transfer : transfers) {
            computedGross = computedGross.add(transfer.amount());
            if (transfer.returnMovement() != null) {
                computedReturns++;
                computedReturn = computedReturn.subtract(
                        transfer.returnMovement().amount());
            }
        }
        BigDecimal computedNet = computedGross.add(computedReturn);
        if (computedNet.compareTo(ZERO) < 0) {
            throw invalidField(trailerNumber);
        }
        return new ParsedBatch(
                sourceFilename,
                header.substring(1, 9),
                expectedBatchId,
                List.copyOf(transfers),
                declaredTransferCount,
                declaredReturnCount,
                declaredGross,
                declaredReturn,
                declaredNet,
                transfers.size(),
                computedReturns,
                computedGross,
                computedReturn,
                computedNet);
    }

    private static void validateDocuments(
            List<Transfer> transfers) throws ProcessorException {
        for (Transfer transfer : transfers) {
            if (!validTaxId(
                        transfer.payerTaxId(),
                        transfer.payerPartyType())) {
                throw new ProcessorException(
                        "INVALID_DOCUMENT",
                        "Type 04 payer document is invalid",
                        transfer.recordNumber(),
                        null);
            }
            if (!validTaxId(
                        transfer.beneficiaryTaxId(),
                        transfer.beneficiaryPartyType())) {
                throw new ProcessorException(
                        "INVALID_DOCUMENT",
                        "Type 04 beneficiary document is invalid",
                        transfer.recordNumber(),
                        null);
            }
        }
    }

    private static void validateSafeIdentifiers(
            ParsedBatch batch) throws ProcessorException {
        List<String> restricted =
                restrictedValues(batch.transfers());
        for (Transfer transfer : batch.transfers()) {
            if (!SAFE_IDENTIFIER.matcher(
                        transfer.transferId()).matches()
                    || !PURPOSE_CODE.matcher(
                        transfer.purposeCode()).matches()
                    || !BENEFICIARY_NAME.matcher(
                        transfer.beneficiaryName()).matches()
                    || containsRestricted(
                        transfer.transferId(),
                        restricted)
                    || containsRestricted(
                        transfer.purposeCode(),
                        restricted)) {
                throw new ProcessorException(
                        "INVALID_IDENTIFIER",
                        "Type 04 transfer identifier or text is unsafe",
                        transfer.recordNumber(),
                        null);
            }
            ReturnMovement returned = transfer.returnMovement();
            if (returned != null
                    && (!SAFE_IDENTIFIER.matcher(
                                returned.returnId()).matches()
                        || !SAFE_IDENTIFIER.matcher(
                                returned.originalTransferId()).matches()
                        || !REASON_CODE.matcher(
                                returned.reasonCode()).matches()
                        || !RETURN_REASON_TEXT.matcher(
                                returned.reasonText()).matches()
                        || containsRestricted(
                                returned.returnId(),
                                restricted)
                        || containsRestricted(
                                returned.originalTransferId(),
                                restricted)
                        || containsRestricted(
                                returned.reasonCode(),
                                restricted))) {
                throw new ProcessorException(
                        "INVALID_IDENTIFIER",
                        "Type 04 return identifier or text is unsafe",
                        returned.recordNumber(),
                        null);
            }
        }
    }

    private static void validateReturnLinkage(
            List<Transfer> transfers) throws ProcessorException {
        for (Transfer transfer : transfers) {
            ReturnMovement returned = transfer.returnMovement();
            if ("RT".equals(transfer.statusCode())) {
                if (returned == null
                        || !returned.originalTransferId().equals(
                                transfer.transferId())
                        || returned.amount().compareTo(
                                transfer.amount()) != 0) {
                    throw new ProcessorException(
                            "RETURN_LINK_MISMATCH",
                            "Type 04 return does not match its transfer",
                            transfer.recordNumber(),
                            null);
                }
            } else if (returned != null) {
                throw new ProcessorException(
                        "RETURN_LINK_MISMATCH",
                        "Type 04 OK transfer unexpectedly has a return",
                        transfer.recordNumber(),
                        null);
            }
        }
    }

    private static void validateUniquenessAndTimestamps(
            List<Transfer> transfers) throws ProcessorException {
        Set<String> movementIds = new HashSet<>();
        for (Transfer transfer : transfers) {
            if (!movementIds.add(transfer.transferId())) {
                throw new ProcessorException(
                        "DUPLICATE_IDENTIFIER",
                        "Type 04 movement identifier is duplicated",
                        transfer.recordNumber(),
                        null);
            }
            ReturnMovement returned = transfer.returnMovement();
            if (returned != null) {
                if (!movementIds.add(returned.returnId())) {
                    throw new ProcessorException(
                            "DUPLICATE_IDENTIFIER",
                            "Type 04 movement identifier is duplicated",
                            returned.recordNumber(),
                            null);
                }
                if (!returned.timestamp().toInstant().isAfter(
                        transfer.timestamp().toInstant())) {
                    throw invalidTimestamp(returned.recordNumber());
                }
            }
        }
    }

    private static LocalDate parseDate(
            String value,
            int recordNumber) throws ProcessorException {
        try {
            return LocalDate.parse(value, SOURCE_DATE);
        } catch (DateTimeParseException exception) {
            throw invalidTimestamp(recordNumber);
        }
    }

    private static OffsetDateTime parseTimestamp(
            String date,
            String time,
            int recordNumber) throws ProcessorException {
        try {
            LocalDate localDate = LocalDate.parse(date, SOURCE_DATE);
            LocalTime localTime = LocalTime.parse(time, SOURCE_TIME);
            LocalDateTime local = LocalDateTime.of(
                    localDate,
                    localTime);
            ZoneRules rules = SAO_PAULO.getRules();
            List<ZoneOffset> offsets = rules.getValidOffsets(local);
            if (offsets.isEmpty()) {
                throw invalidTimestamp(recordNumber);
            }
            return OffsetDateTime.of(local, offsets.getFirst());
        } catch (DateTimeException exception) {
            throw invalidTimestamp(recordNumber);
        }
    }

    private static String rightTildeUnpad(
            String record,
            int start,
            int end,
            int recordNumber) throws ProcessorException {
        String padded = record.substring(start, end);
        int length = padded.length();
        while (length > 0 && padded.charAt(length - 1) == '~') {
            length--;
        }
        String value = padded.substring(0, length);
        if (value.indexOf('~') >= 0) {
            throw new ProcessorException(
                    "INVALID_PADDING",
                    "Type 04 visible padding is invalid",
                    recordNumber,
                    null);
        }
        return value;
    }

    private static BigDecimal parseImpliedMoney(
            String value,
            int recordNumber) throws ProcessorException {
        if (!asciiDigits(value)) {
            throw invalidField(recordNumber);
        }
        return new BigDecimal(value).movePointLeft(2);
    }

    private static int parseBoundedInteger(
            String value,
            int minimum,
            int maximum,
            int recordNumber) throws ProcessorException {
        if (!asciiDigits(value)) {
            throw invalidField(recordNumber);
        }
        int parsed;
        try {
            parsed = Integer.parseInt(value);
        } catch (NumberFormatException exception) {
            throw invalidField(recordNumber);
        }
        if (parsed < minimum || parsed > maximum) {
            throw invalidField(recordNumber);
        }
        return parsed;
    }

    private static boolean validTaxId(String value, char partyType) {
        if (partyType == 'F') {
            return value.startsWith("000")
                    && validCpf(value.substring(3));
        }
        return partyType == 'J' && validCnpj(value);
    }

    private static boolean validCpf(String value) {
        if (!value.matches("[0-9]{11}")
                || allDigitsEqual(value)) {
            return false;
        }
        int first = mod11Digit(value.substring(0, 9), 10);
        int second = mod11Digit(
                value.substring(0, 9) + first,
                11);
        return value.charAt(9) - '0' == first
                && value.charAt(10) - '0' == second;
    }

    private static boolean validCnpj(String value) {
        if (!value.matches("[0-9]{14}")
                || allDigitsEqual(value)) {
            return false;
        }
        int first = cnpjDigit(
                value.substring(0, 12),
                new int[] {5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2});
        int second = cnpjDigit(
                value.substring(0, 12) + first,
                new int[] {6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2});
        return value.charAt(12) - '0' == first
                && value.charAt(13) - '0' == second;
    }

    private static int mod11Digit(String digits, int initialWeight) {
        int total = 0;
        for (int index = 0; index < digits.length(); index++) {
            total += (digits.charAt(index) - '0')
                    * (initialWeight - index);
        }
        int remainder = total % 11;
        return remainder < 2 ? 0 : 11 - remainder;
    }

    private static int cnpjDigit(String digits, int[] weights) {
        int total = 0;
        for (int index = 0; index < digits.length(); index++) {
            total += (digits.charAt(index) - '0') * weights[index];
        }
        int remainder = total % 11;
        return remainder < 2 ? 0 : 11 - remainder;
    }

    private static boolean allDigitsEqual(String value) {
        for (int index = 1; index < value.length(); index++) {
            if (value.charAt(index) != value.charAt(0)) {
                return false;
            }
        }
        return true;
    }

    private static void appendCsvRow(
            StringBuilder output,
            List<String> fields) {
        for (int index = 0; index < fields.size(); index++) {
            if (index > 0) {
                output.append(',');
            }
            output.append(csvField(fields.get(index)));
        }
        output.append('\n');
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

    private static String token(
            String key,
            String canonicalAccount) throws ProcessorException {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(
                    key.getBytes(StandardCharsets.UTF_8),
                    "HmacSHA256"));
            byte[] digest = mac.doFinal(
                    canonicalAccount.getBytes(
                            StandardCharsets.US_ASCII));
            return "tedacct_" + HexFormat.of()
                    .formatHex(digest)
                    .substring(0, 24);
        } catch (GeneralSecurityException exception) {
            throw new ProcessorException(
                    "TOKENIZATION_ERROR",
                    "Cannot tokenize a protected Type 04 account",
                    exception);
        }
    }

    private static String maskTaxId(String value, char partyType) {
        String document = partyType == 'F'
                ? value.substring(3)
                : value;
        return (partyType == 'F' ? "*******" : "**********")
                + document.substring(document.length() - 4);
    }

    private static void validatePrivacyBoundary(
            CharSequence csv,
            List<Transfer> transfers) throws ProcessorException {
        String output = csv.toString();
        for (Transfer transfer : transfers) {
            for (String restricted : transfer.restrictedValues()) {
                if (!restricted.isEmpty()
                        && output.contains(restricted)) {
                    throw new ProcessorException(
                            "PRIVACY_BOUNDARY_VIOLATION",
                            "Sanitized Type 04 CSV contains restricted data",
                            transfer.recordNumber(),
                            null);
                }
            }
        }
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
                "code", "TED_SETTLE04",
                "contract_version", 1,
                "layout_version", "001",
                "number", "04");
        Map<String, Object> lineage = Map.of(
                "manifest_sha256",
                ArtifactIO.sha256(context.sourceManifestBytes()),
                "raw_file", source.filename(),
                "raw_sha256", source.sha256());
        Map<String, Object> controls = Map.of(
                "currency", "BRL",
                "gross_amount", money(output.grossAmount()),
                "net_amount", money(output.netAmount()),
                "return_amount", money(output.returnAmount()),
                "return_count", output.returnCount(),
                "row_count", output.rowCount(),
                "transfer_count", output.transferCount());
        return Map.of(
                "batch_id", context.batchId(),
                "csv_file", csvFile,
                "file_type", fileType,
                "schema_version", 1,
                "source_lineage", lineage,
                "stage_controls", controls);
    }

    private static DiagnosticPrivacy diagnosticPrivacyForRaw(
            byte[] rawBytes) {
        if (rawBytes == null) {
            return DiagnosticPrivacy.fromRestrictedValues(List.of());
        }
        List<String> restricted = new ArrayList<>();
        String text = new String(
                rawBytes,
                StandardCharsets.ISO_8859_1);
        String[] records = text.split("\\r?\\n", -1);
        for (String record : records) {
            if (record.length() >= TRANSFER_BYTES
                    && record.charAt(0) == 'D') {
                String payerTax = record.substring(73, 87);
                String beneficiaryTax = record.substring(112, 126);
                restricted.add(record.substring(61, 73));
                restricted.add(payerTax);
                if (record.charAt(87) == 'F'
                        && payerTax.length() == 14) {
                    restricted.add(payerTax.substring(3));
                }
                restricted.add(record.substring(100, 112));
                restricted.add(beneficiaryTax);
                if (record.charAt(126) == 'F'
                        && beneficiaryTax.length() == 14) {
                    restricted.add(beneficiaryTax.substring(3));
                }
                restricted.add(rightTrimTildes(
                        record.substring(139, 162)));
            } else if (record.length() >= RETURN_BYTES
                    && record.charAt(0) == 'R') {
                restricted.add(rightTrimTildes(
                        record.substring(67, 91)));
            }
        }
        return DiagnosticPrivacy.fromRestrictedValues(restricted);
    }

    private static List<String> restrictedValues(
            List<Transfer> transfers) {
        LinkedHashSet<String> values = new LinkedHashSet<>();
        for (Transfer transfer : transfers) {
            values.addAll(transfer.restrictedValues());
        }
        return List.copyOf(values);
    }

    private static boolean containsRestricted(
            String candidate,
            List<String> restrictedValues) {
        for (String restricted : restrictedValues) {
            if (!restricted.isEmpty()
                    && candidate.contains(restricted)) {
                return true;
            }
        }
        return false;
    }

    private static String rightTrimTildes(String value) {
        int length = value.length();
        while (length > 0 && value.charAt(length - 1) == '~') {
            length--;
        }
        return value.substring(0, length);
    }

    private static boolean validControlObject(JsonNode controls) {
        if (!hasExactFields(controls, SOURCE_CONTROL_FIELDS)
                || !controls.path("currency").isTextual()
                || !"BRL".equals(controls.path("currency").asText())
                || !canonicalUnsignedMoney(
                        controls,
                        "gross_amount")
                || "0.00".equals(
                        controls.path("gross_amount").asText())
                || !canonicalUnsignedMoney(
                        controls,
                        "net_amount")
                || !controls.path("return_amount").isTextual()
                || !CANONICAL_RETURNED_MONEY.matcher(
                        controls.path("return_amount").asText()).matches()
                || !integralInRange(
                        controls.path("return_count"),
                        0,
                        MAX_RETURNS)
                || !integralInRange(
                        controls.path("transfer_count"),
                        1,
                        MAX_TRANSFERS)) {
            return false;
        }
        return true;
    }

    private static boolean canonicalUnsignedMoney(
            JsonNode object,
            String field) {
        JsonNode value = object.path(field);
        return value.isTextual()
                && CANONICAL_UNSIGNED_MONEY.matcher(
                        value.asText()).matches();
    }

    private static boolean integralInRange(
            JsonNode value,
            int minimum,
            int maximum) {
        return value.isIntegralNumber()
                && value.canConvertToInt()
                && value.intValue() >= minimum
                && value.intValue() <= maximum;
    }

    private static boolean hasExactFields(
            JsonNode object,
            Set<String> expected) {
        if (!object.isObject() || object.size() != expected.size()) {
            return false;
        }
        Iterator<String> names = object.fieldNames();
        while (names.hasNext()) {
            if (!expected.contains(names.next())) {
                return false;
            }
        }
        return true;
    }

    private static ProcessorException sourceControlFailure(
            String code,
            ParsedBatch batch) {
        return ProcessorException.type04SourceControlMismatch(
                code,
                batch.declaredTransferCount(),
                batch.declaredReturnCount(),
                money(batch.declaredGrossAmount()),
                money(batch.declaredReturnAmount()),
                money(batch.declaredNetAmount()),
                batch.computedTransferCount(),
                batch.computedReturnCount(),
                money(batch.computedGrossAmount()),
                money(batch.computedReturnAmount()),
                money(batch.computedNetAmount()));
    }

    private static ProcessorException invalidField(int recordNumber) {
        return new ProcessorException(
                "INVALID_FIELD",
                "Type 04 field violates its contract",
                recordNumber,
                null);
    }

    private static ProcessorException invalidTimestamp(
            int recordNumber) {
        return new ProcessorException(
                "INVALID_TIMESTAMP",
                "Type 04 local timestamp is invalid",
                recordNumber,
                null);
    }

    private static ProcessorException invalidManifest() {
        return new ProcessorException(
                "INVALID_MANIFEST",
                "Source manifest does not match Type 04");
    }

    private static boolean asciiDigits(String value) {
        if (value.isEmpty()) {
            return false;
        }
        for (int index = 0; index < value.length(); index++) {
            char character = value.charAt(index);
            if (character < '0' || character > '9') {
                return false;
            }
        }
        return true;
    }

    private static String money(BigDecimal value) {
        return value.setScale(2).toPlainString();
    }

    private static String nullToEmpty(String value) {
        return value == null ? "" : value;
    }

    record SourceDescriptor(
            String filename,
            String sha256,
            long sizeBytes) {
    }

    record MovementSpan(
            int transferIndex,
            Integer returnIndex) {
    }

    /**
     * Dedicated Type 04 HMAC key wrapper.
     */
    record TokenKey(String value) {
    }

    /**
     * Parsed return record whose reason text stays inside the trust boundary.
     */
    record ReturnMovement(
            int recordNumber,
            String returnId,
            String originalTransferId,
            BigDecimal amount,
            OffsetDateTime timestamp,
            String reasonCode,
            String reasonText) {
    }

    /**
     * Parsed transfer and optional immediate full return.
     */
    record Transfer(
            int recordNumber,
            String transferId,
            BigDecimal amount,
            OffsetDateTime timestamp,
            String payerIspb,
            String payerBranch,
            String payerAccount,
            String payerTaxId,
            char payerPartyType,
            String beneficiaryIspb,
            String beneficiaryBranch,
            String beneficiaryAccount,
            String beneficiaryTaxId,
            char beneficiaryPartyType,
            String purposeCode,
            String statusCode,
            String beneficiaryName,
            ReturnMovement returnMovement) {

        String payerAccountInput() {
            return payerIspb + ":" + payerBranch + ":" + payerAccount;
        }

        String beneficiaryAccountInput() {
            return beneficiaryIspb
                    + ":"
                    + beneficiaryBranch
                    + ":"
                    + beneficiaryAccount;
        }

        List<String> restrictedValues() {
            LinkedHashSet<String> values = new LinkedHashSet<>();
            values.add(payerAccount);
            values.add(beneficiaryAccount);
            values.add(payerTaxId);
            values.add(beneficiaryTaxId);
            if (payerPartyType == 'F') {
                values.add(payerTaxId.substring(3));
            }
            if (beneficiaryPartyType == 'F') {
                values.add(beneficiaryTaxId.substring(3));
            }
            values.add(beneficiaryName);
            if (returnMovement != null) {
                values.add(returnMovement.reasonText());
            }
            return List.copyOf(values);
        }
    }

    /**
     * Fully parsed Type 04 batch with declared and independent controls.
     */
    record ParsedBatch(
            String sourceFilename,
            String fileDate,
            String batchId,
            List<Transfer> transfers,
            int declaredTransferCount,
            int declaredReturnCount,
            BigDecimal declaredGrossAmount,
            BigDecimal declaredReturnAmount,
            BigDecimal declaredNetAmount,
            int computedTransferCount,
            int computedReturnCount,
            BigDecimal computedGrossAmount,
            BigDecimal computedReturnAmount,
            BigDecimal computedNetAmount) {
    }

    /**
     * Candidate sanitized bytes and computed publication controls.
     */
    record CsvOutput(
            byte[] bytes,
            int rowCount,
            int transferCount,
            int returnCount,
            BigDecimal grossAmount,
            BigDecimal returnAmount,
            BigDecimal netAmount) {

        CsvOutput {
            bytes = bytes.clone();
        }

        @Override
        public byte[] bytes() {
            return bytes.clone();
        }
    }
}

package com.northwindpay.legacy.type03;

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
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.time.format.ResolverStyle;
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
 * Contract-faithful Type 03 payment-slip settlement converter.
 *
 * <p>The converter validates the complete source in the contract's declared
 * precedence, joins only adjacent {@code A}/{@code B} segment pairs, performs
 * exact decimal aggregation, and crosses the sanitization boundary only after
 * three independent HMAC domains and a whole-output restricted-value scan
 * succeed.
 */
public final class Type03Processor implements BatchProcessor {
    private static final int RECORD_BYTES = 240;
    private static final int TRANSPORT_RECORD_BYTES = 242;
    private static final int MIN_PHYSICAL_RECORDS = 6;
    private static final int MAX_PHYSICAL_RECORDS = 22_002;
    private static final int MAX_SOURCE_BYTES = 5_324_484;
    private static final int MAX_LOTS = 1_000;
    private static final int MAX_SETTLEMENTS = 10_000;
    private static final int MAX_CSV_BYTES = 8_000_000;
    private static final BigDecimal ZERO = new BigDecimal("0.00");
    private static final Pattern BATCH_PATTERN =
            Pattern.compile("B[0-9]{15}");
    private static final Pattern FILENAME_PATTERN = Pattern.compile(
            "NW_PAYMENT_SLIP_([0-9]{8})_(B[0-9]{15})\\.rem");
    private static final Pattern LOT_SEQUENCE_PATTERN =
            Pattern.compile("(?!000000)[0-9]{6}");
    private static final Pattern SAFE_IDENTIFIER =
            Pattern.compile("[A-Z][A-Z0-9]{15}");
    private static final Pattern SAFE_REFERENCE =
            Pattern.compile("[A-Z][A-Z0-9]{19}");
    private static final Pattern BENEFICIARY_NAME =
            Pattern.compile("[A-Z][A-Z0-9 .&/-]{0,39}");
    private static final Pattern CANONICAL_UNSIGNED_MONEY =
            Pattern.compile("(?:0|[1-9][0-9]{0,15})\\.[0-9]{2}");
    private static final DateTimeFormatter SOURCE_DATE =
            DateTimeFormatter.ofPattern("uuuuMMdd", Locale.ROOT)
                    .withResolverStyle(ResolverStyle.STRICT);
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
            "record_length_bytes",
            "sha256",
            "size_bytes");
    private static final Set<String> SOURCE_CONTROL_FIELDS = Set.of(
            "currency",
            "discount_amount",
            "face_amount",
            "fee_amount",
            "logical_count",
            "lot_count",
            "net_amount",
            "orphan_segment_count",
            "physical_record_count");
    private static final String CSV_HEADER = String.join(",",
            "batch_id",
            "source_file",
            "source_record_number_a",
            "source_record_number_b",
            "lot_number",
            "sequence",
            "settlement_id",
            "payment_reference_token",
            "payment_reference_last4",
            "beneficiary_token",
            "beneficiary_tax_id_type",
            "beneficiary_tax_id_masked",
            "bank_account_token",
            "bank_account_last4",
            "due_date",
            "payment_date",
            "face_amount_brl",
            "discount_brl",
            "fee_brl",
            "net_amount_brl",
            "status",
            "bank_reference",
            "client_reference");

    @Override
    public String typeNumber() {
        return "03";
    }

    @Override
    public String typeCode() {
        return "PAYSLIPSET03";
    }

    @Override
    public String layoutVersion() {
        return "001";
    }

    /**
     * Validates, sanitizes, and atomically publishes one Type 03 source.
     *
     * @param context integrity-checked source and publication boundary
     * @return privacy-safe aggregate success evidence
     * @throws ProcessorException when any contract or boundary check fails
     */
    @Override
    public ProcessorResult process(ProcessingContext context)
            throws ProcessorException {
        DiagnosticPrivacy privacy =
                diagnosticPrivacyForRaw(context.sourceArtifact().bytes());
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
                        "Acquired source does not match Type 03 metadata");
            }
            TokenKeys keys = validateTokenKeys(context.configuration());
            ParsedBatch parsed = parseRaw(
                    artifact.bytes(),
                    source.filename(),
                    context.batchId());
            validateSourceControls(parsed, context.sourceManifest());
            CsvOutput csv = renderCsv(
                    parsed,
                    source.filename(),
                    keys);
            String csvFilename = source.filename().substring(
                    0,
                    source.filename().length() - ".rem".length()) + ".csv";
            String csvSha256 = ArtifactIO.sha256(csv.bytes());
            ArtifactIO.PublishedCsv published = ArtifactIO.publishSanitized(
                    context,
                    csvFilename,
                    csv.bytes(),
                    sanitizedManifest(
                            context,
                            source,
                            csvFilename,
                            csvSha256,
                            csv));
            return ProcessorResult.type03Succeeded(
                    context.batchId(),
                    published.filename(),
                    published.sha256(),
                    csv.rowCount(),
                    money(csv.faceAmount()),
                    money(csv.discountAmount()),
                    money(csv.feeAmount()),
                    money(csv.netAmount()),
                    csv.orphanSegmentCount());
        } catch (ProcessorException exception) {
            throw exception.withDiagnosticPrivacy(privacy);
        }
    }

    /**
     * Parses and validates all non-control Type 03 source rules.
     *
     * <p>Control reconciliation is deliberately separate so source-manifest
     * declarations can first be compared with raw trailer declarations.
     */
    static ParsedBatch parseRaw(
            byte[] rawBytes,
            String sourceFilename,
            String expectedBatchId) throws ProcessorException {
        DiagnosticPrivacy privacy = diagnosticPrivacyForRaw(rawBytes);
        try {
            List<String> records = decodeRecords(rawBytes);
            List<LotSpan> lotSpans = validateGrammar(records);
            validateStaticFields(
                    records,
                    lotSpans,
                    sourceFilename,
                    expectedBatchId);
            ParsedBatch parsed = parseLexicalFields(
                    records,
                    lotSpans,
                    sourceFilename,
                    expectedBatchId);
            validateDocuments(parsed.settlements());
            validateSafeIdentifiers(parsed);
            validateSegmentPairs(parsed);
            validateUniquenessAndBusinessDates(parsed);
            return parsed;
        } catch (ProcessorException exception) {
            throw exception.withDiagnosticPrivacy(privacy);
        }
    }

    /**
     * Validates manifest-to-source equality and all raw aggregate controls in
     * their contract order.
     */
    static void validateSourceControls(
            ParsedBatch batch,
            JsonNode manifest) throws ProcessorException {
        JsonNode controls = manifest.path("source_controls");
        if (!validControlObject(controls)) {
            throw invalidManifest();
        }
        int manifestLotCount = controls.path("lot_count").intValue();
        int manifestPhysical =
                controls.path("physical_record_count").intValue();
        int manifestLogical = controls.path("logical_count").intValue();
        String manifestFace = controls.path("face_amount").textValue();
        String manifestDiscount =
                controls.path("discount_amount").textValue();
        String manifestFee = controls.path("fee_amount").textValue();
        String manifestNet = controls.path("net_amount").textValue();
        if (manifestLotCount != batch.declaredLotCount()
                || manifestPhysical
                        != batch.declaredPhysicalRecordCount()
                || manifestLogical != batch.declaredLogicalCount()
                || !manifestFace.equals(money(
                        batch.declaredFaceAmount()))
                || !manifestDiscount.equals(money(
                        batch.declaredDiscountAmount()))
                || !manifestFee.equals(money(
                        batch.declaredFeeAmount()))
                || !manifestNet.equals(money(
                        batch.declaredNetAmount()))) {
            throw invalidManifest();
        }

        for (Lot lot : batch.lots()) {
            if (lot.declaredLogicalCount()
                    != lot.settlements().size()) {
                throw sourceControlFailure(
                        "SOURCE_CONTROL_LOGICAL_COUNT_MISMATCH",
                        batch);
            }
            if (lot.declaredFaceAmount().compareTo(
                    lot.computedFaceAmount()) != 0) {
                throw sourceControlFailure(
                        "SOURCE_CONTROL_FACE_MISMATCH",
                        batch);
            }
            if (lot.declaredDiscountAmount().compareTo(
                    lot.computedDiscountAmount()) != 0) {
                throw sourceControlFailure(
                        "SOURCE_CONTROL_DISCOUNT_MISMATCH",
                        batch);
            }
            if (lot.declaredFeeAmount().compareTo(
                    lot.computedFeeAmount()) != 0) {
                throw sourceControlFailure(
                        "SOURCE_CONTROL_FEE_MISMATCH",
                        batch);
            }
            if (lot.declaredNetAmount().compareTo(
                    lot.computedNetAmount()) != 0) {
                throw sourceControlFailure(
                        "SOURCE_CONTROL_NET_MISMATCH",
                        batch);
            }
        }
        if (batch.declaredLotCount() != batch.computedLotCount()) {
            throw sourceControlFailure(
                    "SOURCE_CONTROL_LOT_COUNT_MISMATCH",
                    batch);
        }
        if (batch.declaredPhysicalRecordCount()
                != batch.computedPhysicalRecordCount()) {
            throw sourceControlFailure(
                    "SOURCE_CONTROL_PHYSICAL_COUNT_MISMATCH",
                    batch);
        }
        if (batch.declaredLogicalCount()
                != batch.computedLogicalCount()) {
            throw sourceControlFailure(
                    "SOURCE_CONTROL_LOGICAL_COUNT_MISMATCH",
                    batch);
        }
        if (batch.declaredFaceAmount().compareTo(
                batch.computedFaceAmount()) != 0) {
            throw sourceControlFailure(
                    "SOURCE_CONTROL_FACE_MISMATCH",
                    batch);
        }
        if (batch.declaredDiscountAmount().compareTo(
                batch.computedDiscountAmount()) != 0) {
            throw sourceControlFailure(
                    "SOURCE_CONTROL_DISCOUNT_MISMATCH",
                    batch);
        }
        if (batch.declaredFeeAmount().compareTo(
                batch.computedFeeAmount()) != 0) {
            throw sourceControlFailure(
                    "SOURCE_CONTROL_FEE_MISMATCH",
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
     * Renders canonical UTF-8/LF CSV and applies the whole-output privacy
     * scan before returning any publishable bytes.
     */
    static CsvOutput renderCsv(
            ParsedBatch batch,
            String sourceFilename,
            TokenKeys keys) throws ProcessorException {
        StringBuilder rendered =
                new StringBuilder(CSV_HEADER).append('\n');
        for (Settlement settlement : batch.settlements()) {
            String documentType = "1".equals(
                    settlement.taxIdType()) ? "CPF" : "CNPJ";
            String document = settlement.document();
            List<String> fields = List.of(
                    batch.batchId(),
                    sourceFilename,
                    Integer.toString(settlement.recordNumberA()),
                    Integer.toString(settlement.recordNumberB()),
                    settlement.lotNumberA(),
                    settlement.sequenceA(),
                    settlement.settlementIdA(),
                    token(
                            "payref",
                            keys.paymentReferenceKey(),
                            settlement.paymentReference()),
                    lastFour(settlement.paymentReference()),
                    token(
                            "party",
                            keys.partyKey(),
                            settlement.beneficiaryName()),
                    documentType,
                    ("CPF".equals(documentType)
                            ? "*******"
                            : "**********")
                            + lastFour(document),
                    token(
                            "acct",
                            keys.accountKey(),
                            settlement.canonicalAccount()),
                    lastFour(settlement.accountNumber()),
                    isoDate(settlement.dueDate()),
                    isoDate(settlement.paymentDate()),
                    money(settlement.faceAmount()),
                    money(settlement.discountAmount()),
                    money(settlement.feeAmount()),
                    money(settlement.netAmount()),
                    "SETTLED",
                    settlement.bankReference(),
                    settlement.clientReference());
            for (int index = 0; index < fields.size(); index++) {
                if (index > 0) {
                    rendered.append(',');
                }
                rendered.append(csvField(fields.get(index)));
            }
            rendered.append('\n');
        }
        byte[] bytes = rendered.toString()
                .getBytes(StandardCharsets.UTF_8);
        if (bytes.length > MAX_CSV_BYTES) {
            throw new ProcessorException(
                    "INVALID_TRANSPORT",
                    "Sanitized Type 03 CSV exceeds its contract limit");
        }
        validatePrivacyBoundary(rendered, batch.settlements());
        return new CsvOutput(
                bytes,
                batch.computedLogicalCount(),
                batch.computedFaceAmount(),
                batch.computedDiscountAmount(),
                batch.computedFeeAmount(),
                batch.computedNetAmount(),
                batch.computedOrphanSegmentCount());
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
                || !"03".equals(fileType.path("number").asText())
                || !fileType.path("code").isTextual()
                || !"PAYSLIPSET03".equals(
                        fileType.path("code").asText())
                || !fileType.path("layout_version").isTextual()
                || !"001".equals(
                        fileType.path("layout_version").asText())
                || !fileType.path("contract_version").isIntegralNumber()
                || !fileType.path(
                        "contract_version").canConvertToInt()
                || fileType.path("contract_version").intValue() != 1
                || !hasExactFields(sourceFile, SOURCE_FILE_FIELDS)
                || !sourceFile.path("name").isTextual()
                || !filenameMatch.matches()
                || !batchId.equals(filenameMatch.group(2))
                || !batchId.substring(1, 9).equals(
                        filenameMatch.group(1))
                || !sourceFile.path("sha256").isTextual()
                || !sha256.matches("[0-9a-f]{64}")
                || !sourceFile.path("size_bytes").isIntegralNumber()
                || !sourceFile.path("size_bytes").canConvertToLong()
                || sizeBytes < MIN_PHYSICAL_RECORDS
                        * TRANSPORT_RECORD_BYTES
                || sizeBytes > MAX_SOURCE_BYTES
                || sizeBytes % TRANSPORT_RECORD_BYTES != 0
                || !sourceFile.path("encoding").isTextual()
                || !"US-ASCII".equals(
                        sourceFile.path("encoding").asText())
                || !sourceFile.path("line_ending").isTextual()
                || !"CRLF".equals(
                        sourceFile.path("line_ending").asText())
                || !sourceFile.path("final_newline").isTextual()
                || !"required".equals(
                        sourceFile.path("final_newline").asText())
                || !sourceFile.path(
                        "record_length_bytes").isIntegralNumber()
                || !sourceFile.path(
                        "record_length_bytes").canConvertToInt()
                || sourceFile.path(
                        "record_length_bytes").intValue()
                        != RECORD_BYTES
                || !validControlObject(
                        manifest.path("source_controls"))) {
            throw invalidManifest();
        }
        return new SourceDescriptor(filename, sha256, sizeBytes);
    }

    private static TokenKeys validateTokenKeys(
            Configuration configuration) throws ProcessorException {
        String payment = configuration.paymentReferenceKey();
        String party = configuration.partyTokenKey();
        String account = configuration.accountTokenKey();
        if (payment == null || payment.isBlank()
                || party == null || party.isBlank()
                || account == null || account.isBlank()) {
            throw new ProcessorException(
                    "TOKENIZATION_KEY_MISSING",
                    "Type 03 requires all three tokenization domains");
        }
        Set<String> type03Keys = new HashSet<>(
                List.of(payment, party, account));
        if (type03Keys.size() != 3
                || equalsNonBlank(payment, configuration.tokenizationKey())
                || equalsNonBlank(party, configuration.tokenizationKey())
                || equalsNonBlank(account, configuration.tokenizationKey())
                || equalsNonBlank(
                        payment,
                        configuration.documentTokenKey())
                || equalsNonBlank(
                        party,
                        configuration.documentTokenKey())
                || equalsNonBlank(
                        account,
                        configuration.documentTokenKey())) {
            throw new ProcessorException(
                    "TOKENIZATION_KEY_REUSE",
                    "Type 03 tokenization keys are not independent");
        }
        return new TokenKeys(payment, party, account);
    }

    private static boolean equalsNonBlank(
            String first,
            String second) {
        return second != null
                && !second.isBlank()
                && first.equals(second);
    }

    private static List<String> decodeRecords(byte[] rawBytes)
            throws ProcessorException {
        if (rawBytes.length
                    < MIN_PHYSICAL_RECORDS * TRANSPORT_RECORD_BYTES
                || rawBytes.length > MAX_SOURCE_BYTES) {
            throw new ProcessorException(
                    "INVALID_SOURCE_SIZE",
                    "Type 03 source size is outside contract bounds");
        }
        for (byte value : rawBytes) {
            if ((value & 0xff) > 0x7f) {
                throw new ProcessorException(
                        "INVALID_ASCII",
                        "Type 03 source is not strict US-ASCII");
            }
        }
        if (rawBytes.length < 2
                || rawBytes[rawBytes.length - 2] != '\r'
                || rawBytes[rawBytes.length - 1] != '\n') {
            throw new ProcessorException(
                    "INVALID_TRANSPORT",
                    "Type 03 source requires a final CRLF");
        }
        int physicalRecordStart = 0;
        for (int index = 0; index < rawBytes.length; index++) {
            byte value = rawBytes[index];
            if (value == '\r') {
                if (index + 1 >= rawBytes.length
                        || rawBytes[index + 1] != '\n') {
                    throw new ProcessorException(
                            "INVALID_TRANSPORT",
                            "Type 03 source contains a bare CR");
                }
                if (index == physicalRecordStart) {
                    throw new ProcessorException(
                            "INVALID_TRANSPORT",
                            "Type 03 source contains a blank record");
                }
            } else if (value == '\n'
                    && (index == 0 || rawBytes[index - 1] != '\r')) {
                throw new ProcessorException(
                        "INVALID_TRANSPORT",
                        "Type 03 source contains a bare LF");
            } else if (value == '\n') {
                physicalRecordStart = index + 1;
            }
        }
        String text = new String(rawBytes, StandardCharsets.US_ASCII);
        String[] split = text.substring(0, text.length() - 2)
                .split("\\r\\n", -1);
        for (int index = 0; index < split.length; index++) {
            if (split[index].length() != RECORD_BYTES) {
                throw new ProcessorException(
                        "INVALID_RECORD_LENGTH",
                        "Type 03 record is not exactly 240 bytes",
                        index + 1,
                        null);
            }
        }
        if (split.length < MIN_PHYSICAL_RECORDS
                || split.length > MAX_PHYSICAL_RECORDS) {
            throw new ProcessorException(
                    "INVALID_RECORD_SEQUENCE",
                    "Type 03 physical record count is outside bounds");
        }
        return List.of(split);
    }

    private static List<LotSpan> validateGrammar(
            List<String> records) throws ProcessorException {
        if (records.getFirst().charAt(0) != 'H'
                || records.getLast().charAt(0) != 'Z') {
            throw new ProcessorException(
                    "INVALID_RECORD_SEQUENCE",
                    "Type 03 header or file trailer is misplaced");
        }
        List<LotSpan> spans = new ArrayList<>();
        int logicalRows = 0;
        int index = 1;
        int last = records.size() - 1;
        while (index < last) {
            if (records.get(index).charAt(0) != 'L') {
                throw new ProcessorException(
                        "INVALID_RECORD_SEQUENCE",
                        "Type 03 lot header is misplaced",
                        index + 1,
                        null);
            }
            int headerIndex = index++;
            List<PairSpan> pairs = new ArrayList<>();
            while (index < last
                    && records.get(index).charAt(0) == 'A') {
                int financialIndex = index++;
                if (index >= last
                        || records.get(index).charAt(0) != 'B') {
                    throw new ProcessorException(
                            "SEGMENT_PAIR_MISMATCH",
                            "Type 03 financial segment lacks its beneficiary",
                            Math.min(index + 1, records.size()),
                            null);
                }
                pairs.add(new PairSpan(financialIndex, index++));
                logicalRows++;
                if (logicalRows > MAX_SETTLEMENTS) {
                    throw new ProcessorException(
                            "INVALID_SOURCE_SIZE",
                            "Type 03 logical-row limit is exceeded");
                }
            }
            if (pairs.isEmpty()
                    || index >= last
                    || records.get(index).charAt(0) != 'T') {
                throw new ProcessorException(
                        "INVALID_RECORD_SEQUENCE",
                        "Type 03 lot grammar is invalid",
                        Math.min(index + 1, records.size()),
                        null);
            }
            spans.add(new LotSpan(
                    headerIndex,
                    List.copyOf(pairs),
                    index++));
            if (spans.size() > MAX_LOTS) {
                throw new ProcessorException(
                        "INVALID_SOURCE_SIZE",
                        "Type 03 lot limit is exceeded");
            }
        }
        if (index != last || spans.isEmpty()) {
            throw new ProcessorException(
                    "INVALID_RECORD_SEQUENCE",
                    "Type 03 source does not match its grammar");
        }
        return List.copyOf(spans);
    }

    private static void validateStaticFields(
            List<String> records,
            List<LotSpan> spans,
            String sourceFilename,
            String expectedBatchId) throws ProcessorException {
        String header = records.getFirst();
        validateFiller(header, 54, 1);
        parseDate(header.substring(1, 9), 1);
        String batchId = header.substring(9, 25);
        Matcher filename = FILENAME_PATTERN.matcher(sourceFilename);
        if (!"PAYSLIPSET03".equals(header.substring(25, 37))
                || !"001".equals(header.substring(37, 40))
                || !"NWP00001".equals(header.substring(40, 48))
                || !filename.matches()
                || !expectedBatchId.equals(batchId)
                || !filename.group(1).equals(header.substring(1, 9))
                || !filename.group(2).equals(batchId)
                || !batchId.substring(1, 9).equals(
                        header.substring(1, 9))) {
            throw new ProcessorException(
                    "INVALID_FIELD",
                    "Type 03 header, filename, and request do not agree",
                    1,
                    null);
        }
        for (LotSpan span : spans) {
            String lotHeader = records.get(span.headerIndex());
            validateFiller(
                    lotHeader,
                    62,
                    span.headerIndex() + 1);
            parseDate(
                    lotHeader.substring(22, 30),
                    span.headerIndex() + 1);
            if (!"SLIPSETTLE01".equals(
                        lotHeader.substring(7, 19))
                    || !"BRL".equals(lotHeader.substring(19, 22))
                    || !batchId.equals(
                        lotHeader.substring(30, 46))) {
                throw invalidField(span.headerIndex() + 1);
            }
            for (PairSpan pair : span.pairs()) {
                String financial = records.get(
                        pair.financialIndex());
                validateFiller(
                        financial,
                        154,
                        pair.financialIndex() + 1);
                parseDate(
                        financial.substring(92, 100),
                        pair.financialIndex() + 1);
                parseDate(
                        financial.substring(100, 108),
                        pair.financialIndex() + 1);
                if (!"00".equals(financial.substring(132, 134))) {
                    throw invalidField(pair.financialIndex() + 1);
                }
                validateFiller(
                        records.get(pair.beneficiaryIndex()),
                        125,
                        pair.beneficiaryIndex() + 1);
            }
            String lotTrailer = records.get(span.trailerIndex());
            validateFiller(
                    lotTrailer,
                    89,
                    span.trailerIndex() + 1);
            if (!batchId.equals(lotTrailer.substring(73, 89))) {
                throw invalidField(span.trailerIndex() + 1);
            }
        }
        String fileTrailer = records.getLast();
        validateFiller(fileTrailer, 50, records.size());
        if (!batchId.equals(fileTrailer.substring(34, 50))) {
            throw invalidField(records.size());
        }
    }

    private static ParsedBatch parseLexicalFields(
            List<String> records,
            List<LotSpan> spans,
            String sourceFilename,
            String expectedBatchId) throws ProcessorException {
        String header = records.getFirst();
        String fileDateLexeme = header.substring(1, 9);
        String batchId = header.substring(9, 25);
        if (!BATCH_PATTERN.matcher(batchId).matches()
                || !asciiDigits(header.substring(48, 54))
                || !header.substring(48, 54).equals(
                        batchId.substring(batchId.length() - 6))) {
            throw invalidField(1);
        }

        List<Lot> lots = new ArrayList<>();
        List<Settlement> settlements = new ArrayList<>();
        for (LotSpan span : spans) {
            String lotHeader = records.get(span.headerIndex());
            String lotNumber = lotHeader.substring(1, 7);
            if (!LOT_SEQUENCE_PATTERN.matcher(lotNumber).matches()) {
                throw invalidField(span.headerIndex() + 1);
            }
            LocalDate settlementDate = parseDate(
                    lotHeader.substring(22, 30),
                    span.headerIndex() + 1);
            String originatorId = lotHeader.substring(46, 62);
            List<Settlement> lotSettlements = new ArrayList<>();
            for (PairSpan pair : span.pairs()) {
                String financial = records.get(
                        pair.financialIndex());
                String beneficiary = records.get(
                        pair.beneficiaryIndex());
                String lotA = financial.substring(1, 7);
                String sequenceA = financial.substring(7, 13);
                String paymentReference =
                        financial.substring(29, 77);
                BigDecimal face = parseImpliedMoney(
                        financial.substring(77, 92),
                        pair.financialIndex() + 1);
                BigDecimal discount = parseImpliedMoney(
                        financial.substring(108, 120),
                        pair.financialIndex() + 1);
                BigDecimal fee = parseImpliedMoney(
                        financial.substring(120, 132),
                        pair.financialIndex() + 1);
                if (!LOT_SEQUENCE_PATTERN.matcher(lotA).matches()
                        || !LOT_SEQUENCE_PATTERN.matcher(
                                sequenceA).matches()
                        || !asciiDigits(paymentReference)
                        || face.compareTo(ZERO) <= 0
                        || discount.compareTo(face) > 0
                        || face.subtract(discount).add(fee)
                                .compareTo(ZERO) < 0) {
                    throw invalidField(pair.financialIndex() + 1);
                }

                String lotB = beneficiary.substring(1, 7);
                String sequenceB = beneficiary.substring(7, 13);
                String taxIdType = beneficiary.substring(29, 30);
                String taxIdTransport =
                        beneficiary.substring(30, 44);
                String paddedName = beneficiary.substring(44, 84);
                String beneficiaryName = rightTrimSpaces(paddedName);
                String bankCode = beneficiary.substring(84, 87);
                String branchNumber =
                        beneficiary.substring(87, 92);
                String accountNumber =
                        beneficiary.substring(92, 104);
                if (!LOT_SEQUENCE_PATTERN.matcher(lotB).matches()
                        || !LOT_SEQUENCE_PATTERN.matcher(
                                sequenceB).matches()
                        || (!"1".equals(taxIdType)
                                && !"2".equals(taxIdType))
                        || !asciiDigits(taxIdTransport)
                        || !paddedName.equals(
                                padRight(beneficiaryName, 40))
                        || !BENEFICIARY_NAME.matcher(
                                beneficiaryName).matches()
                        || !bankCode.matches("(?!000)[0-9]{3}")
                        || !asciiDigits(branchNumber)
                        || !asciiDigits(accountNumber)) {
                    throw invalidField(pair.beneficiaryIndex() + 1);
                }
                Settlement settlement = new Settlement(
                        pair.financialIndex() + 1,
                        pair.beneficiaryIndex() + 1,
                        lotA,
                        sequenceA,
                        financial.substring(13, 29),
                        paymentReference,
                        face,
                        parseDate(
                                financial.substring(92, 100),
                                pair.financialIndex() + 1),
                        parseDate(
                                financial.substring(100, 108),
                                pair.financialIndex() + 1),
                        discount,
                        fee,
                        financial.substring(134, 154),
                        lotB,
                        sequenceB,
                        beneficiary.substring(13, 29),
                        taxIdType,
                        taxIdTransport,
                        beneficiaryName,
                        bankCode,
                        branchNumber,
                        accountNumber,
                        beneficiary.substring(104, 105),
                        beneficiary.substring(105, 125));
                lotSettlements.add(settlement);
                settlements.add(settlement);
            }
            String trailer = records.get(span.trailerIndex());
            String trailerLot = trailer.substring(1, 7);
            int declaredCount = parseBoundedInteger(
                    trailer.substring(7, 13),
                    1,
                    MAX_SETTLEMENTS,
                    span.trailerIndex() + 1);
            if (!LOT_SEQUENCE_PATTERN.matcher(trailerLot).matches()
                    || !lotNumber.equals(trailerLot)) {
                throw invalidField(span.trailerIndex() + 1);
            }
            lots.add(new Lot(
                    span.headerIndex() + 1,
                    lotNumber,
                    settlementDate,
                    originatorId,
                    List.copyOf(lotSettlements),
                    declaredCount,
                    parseImpliedMoney(
                            trailer.substring(13, 28),
                            span.trailerIndex() + 1),
                    parseImpliedMoney(
                            trailer.substring(28, 43),
                            span.trailerIndex() + 1),
                    parseImpliedMoney(
                            trailer.substring(43, 58),
                            span.trailerIndex() + 1),
                    parseImpliedMoney(
                            trailer.substring(58, 73),
                            span.trailerIndex() + 1)));
        }
        String fileTrailer = records.getLast();
        int declaredLotCount = parseBoundedInteger(
                fileTrailer.substring(1, 7),
                1,
                MAX_LOTS,
                records.size());
        int declaredPhysical = parseBoundedInteger(
                fileTrailer.substring(7, 13),
                MIN_PHYSICAL_RECORDS,
                MAX_PHYSICAL_RECORDS,
                records.size());
        int declaredLogical = parseBoundedInteger(
                fileTrailer.substring(13, 19),
                1,
                MAX_SETTLEMENTS,
                records.size());
        BigDecimal declaredNet = parseImpliedMoney(
                fileTrailer.substring(19, 34),
                records.size());
        BigDecimal declaredFace = sumLots(
                lots,
                Lot::declaredFaceAmount);
        BigDecimal declaredDiscount = sumLots(
                lots,
                Lot::declaredDiscountAmount);
        BigDecimal declaredFee = sumLots(
                lots,
                Lot::declaredFeeAmount);
        BigDecimal computedFace = sumSettlements(
                settlements,
                Settlement::faceAmount);
        BigDecimal computedDiscount = sumSettlements(
                settlements,
                Settlement::discountAmount);
        BigDecimal computedFee = sumSettlements(
                settlements,
                Settlement::feeAmount);
        BigDecimal computedNet = sumSettlements(
                settlements,
                Settlement::netAmount);
        return new ParsedBatch(
                sourceFilename,
                fileDateLexeme,
                parseDate(fileDateLexeme, 1),
                expectedBatchId,
                List.copyOf(lots),
                List.copyOf(settlements),
                declaredLotCount,
                declaredPhysical,
                declaredLogical,
                declaredFace,
                declaredDiscount,
                declaredFee,
                declaredNet,
                lots.size(),
                records.size(),
                settlements.size(),
                computedFace,
                computedDiscount,
                computedFee,
                computedNet,
                0);
    }

    private static void validateDocuments(
            List<Settlement> settlements) throws ProcessorException {
        for (Settlement settlement : settlements) {
            boolean valid;
            if ("1".equals(settlement.taxIdType())) {
                valid = settlement.taxIdTransport().startsWith("000")
                        && validCpf(settlement.document());
            } else {
                valid = validCnpj(settlement.document());
            }
            if (!valid) {
                throw new ProcessorException(
                        "INVALID_DOCUMENT",
                        "Type 03 beneficiary document is invalid",
                        settlement.recordNumberB(),
                        null);
            }
        }
    }

    private static void validateSafeIdentifiers(
            ParsedBatch batch) throws ProcessorException {
        List<String> restricted = restrictedValues(batch.settlements());
        for (Lot lot : batch.lots()) {
            if (!SAFE_IDENTIFIER.matcher(
                    lot.originatorId()).matches()) {
                throw new ProcessorException(
                        "INVALID_IDENTIFIER",
                        "Type 03 lot identifier is unsafe",
                        lot.recordNumber(),
                        null);
            }
        }
        for (Settlement settlement : batch.settlements()) {
            if (!SAFE_IDENTIFIER.matcher(
                        settlement.settlementIdA()).matches()
                    || !SAFE_REFERENCE.matcher(
                        settlement.bankReference()).matches()
                    || containsRestricted(
                        settlement.settlementIdA(),
                        restricted)
                    || containsRestricted(
                        settlement.bankReference(),
                        restricted)) {
                throw new ProcessorException(
                        "INVALID_IDENTIFIER",
                        "Type 03 financial identifier is unsafe",
                        settlement.recordNumberA(),
                        null);
            }
            if (!SAFE_IDENTIFIER.matcher(
                        settlement.settlementIdB()).matches()
                    || !settlement.accountCheckDigit()
                        .matches("[A-Z0-9]")
                    || !SAFE_REFERENCE.matcher(
                        settlement.clientReference()).matches()
                    || containsRestricted(
                        settlement.settlementIdB(),
                        restricted)
                    || containsRestricted(
                        settlement.clientReference(),
                        restricted)) {
                throw new ProcessorException(
                        "INVALID_IDENTIFIER",
                        "Type 03 beneficiary identifier is unsafe",
                        settlement.recordNumberB(),
                        null);
            }
        }
    }

    private static void validateSegmentPairs(
            ParsedBatch batch) throws ProcessorException {
        for (Lot lot : batch.lots()) {
            for (Settlement settlement : lot.settlements()) {
                if (!lot.lotNumber().equals(
                            settlement.lotNumberA())
                        || !lot.lotNumber().equals(
                            settlement.lotNumberB())
                        || !settlement.sequenceA().equals(
                            settlement.sequenceB())
                        || !settlement.settlementIdA().equals(
                            settlement.settlementIdB())) {
                    throw new ProcessorException(
                            "SEGMENT_PAIR_MISMATCH",
                            "Type 03 adjacent segments do not form one row",
                            settlement.recordNumberB(),
                            null);
                }
            }
        }
    }

    private static void validateUniquenessAndBusinessDates(
            ParsedBatch batch) throws ProcessorException {
        Set<String> lotNumbers = new HashSet<>();
        Set<String> settlementIds = new HashSet<>();
        for (Lot lot : batch.lots()) {
            if (!lotNumbers.add(lot.lotNumber())) {
                throw new ProcessorException(
                        "DUPLICATE_IDENTIFIER",
                        "Type 03 lot number is duplicated",
                        lot.recordNumber(),
                        null);
            }
            if (!batch.fileDate().equals(lot.settlementDate())) {
                throw new ProcessorException(
                        "INVALID_BUSINESS_DATE",
                        "Type 03 lot date does not match the file date",
                        lot.recordNumber(),
                        null);
            }
            Set<String> sequences = new HashSet<>();
            for (Settlement settlement : lot.settlements()) {
                if (!sequences.add(settlement.sequenceA())
                        || !settlementIds.add(
                                settlement.settlementIdA())) {
                    throw new ProcessorException(
                            "DUPLICATE_IDENTIFIER",
                            "Type 03 settlement identity is duplicated",
                            settlement.recordNumberA(),
                            null);
                }
                if (!lot.settlementDate().equals(
                            settlement.paymentDate())
                        || settlement.paymentDate().isAfter(
                            settlement.dueDate())) {
                    throw new ProcessorException(
                            "INVALID_BUSINESS_DATE",
                            "Type 03 settlement dates are inconsistent",
                            settlement.recordNumberA(),
                            null);
                }
            }
        }
    }

    private static void validateFiller(
            String record,
            int start,
            int recordNumber) throws ProcessorException {
        for (int index = start; index < record.length(); index++) {
            if (record.charAt(index) != '~') {
                throw new ProcessorException(
                        "INVALID_FILLER",
                        "Type 03 reserved filler is invalid",
                        recordNumber,
                        null);
            }
        }
    }

    private static LocalDate parseDate(
            String value,
            int recordNumber) throws ProcessorException {
        try {
            return LocalDate.parse(value, SOURCE_DATE);
        } catch (DateTimeParseException exception) {
            throw invalidField(recordNumber);
        }
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

    private static ProcessorException invalidField(int recordNumber) {
        return new ProcessorException(
                "INVALID_FIELD",
                "Type 03 field violates its contract",
                recordNumber,
                null);
    }

    private static ProcessorException invalidManifest() {
        return new ProcessorException(
                "INVALID_MANIFEST",
                "Source manifest does not match Type 03");
    }

    private static boolean validControlObject(JsonNode controls) {
        if (!hasExactFields(controls, SOURCE_CONTROL_FIELDS)
                || !controls.path("currency").isTextual()
                || !"BRL".equals(controls.path("currency").asText())
                || !canonicalMoneyField(controls, "discount_amount")
                || !canonicalMoneyField(controls, "face_amount")
                || "0.00".equals(
                        controls.path("face_amount").asText())
                || !canonicalMoneyField(controls, "fee_amount")
                || !canonicalMoneyField(controls, "net_amount")
                || !integralInRange(
                        controls.path("logical_count"),
                        1,
                        MAX_SETTLEMENTS)
                || !integralInRange(
                        controls.path("lot_count"),
                        1,
                        MAX_LOTS)
                || !integralInRange(
                        controls.path("physical_record_count"),
                        MIN_PHYSICAL_RECORDS,
                        MAX_PHYSICAL_RECORDS)
                || !controls.path(
                        "orphan_segment_count").isIntegralNumber()
                || !controls.path(
                        "orphan_segment_count").canConvertToInt()
                || controls.path(
                        "orphan_segment_count").intValue() != 0) {
            return false;
        }
        return true;
    }

    private static boolean canonicalMoneyField(
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
        return ProcessorException.type03SourceControlMismatch(
                code,
                batch.declaredLotCount(),
                batch.declaredPhysicalRecordCount(),
                batch.declaredLogicalCount(),
                money(batch.declaredFaceAmount()),
                money(batch.declaredDiscountAmount()),
                money(batch.declaredFeeAmount()),
                money(batch.declaredNetAmount()),
                batch.computedLotCount(),
                batch.computedPhysicalRecordCount(),
                batch.computedLogicalCount(),
                money(batch.computedFaceAmount()),
                money(batch.computedDiscountAmount()),
                money(batch.computedFeeAmount()),
                money(batch.computedNetAmount()),
                batch.computedOrphanSegmentCount());
    }

    private static String token(
            String prefix,
            String key,
            String value) throws ProcessorException {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(
                    key.getBytes(StandardCharsets.UTF_8),
                    "HmacSHA256"));
            byte[] digest = mac.doFinal(
                    value.getBytes(StandardCharsets.US_ASCII));
            return prefix + "_" + HexFormat.of()
                    .formatHex(digest)
                    .substring(0, 24);
        } catch (GeneralSecurityException exception) {
            throw new ProcessorException(
                    "TOKENIZATION_ERROR",
                    "Cannot tokenize a protected Type 03 field",
                    exception);
        }
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
            List<Settlement> settlements) throws ProcessorException {
        String output = csv.toString();
        for (Settlement settlement : settlements) {
            for (String restricted : settlement.restrictedValues()) {
                if (!restricted.isEmpty()
                        && output.contains(restricted)) {
                    throw new ProcessorException(
                            "PRIVACY_BOUNDARY_VIOLATION",
                            "Sanitized Type 03 CSV contains restricted data",
                            settlement.recordNumberB(),
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
                "code", "PAYSLIPSET03",
                "contract_version", 1,
                "layout_version", "001",
                "number", "03");
        Map<String, Object> lineage = Map.of(
                "manifest_sha256",
                ArtifactIO.sha256(context.sourceManifestBytes()),
                "raw_file", source.filename(),
                "raw_sha256", source.sha256());
        Map<String, Object> controls = Map.of(
                "currency", "BRL",
                "discount_amount", money(output.discountAmount()),
                "face_amount", money(output.faceAmount()),
                "fee_amount", money(output.feeAmount()),
                "net_amount", money(output.netAmount()),
                "orphan_segment_count", output.orphanSegmentCount(),
                "row_count", output.rowCount());
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
        List<String> restricted = new ArrayList<>();
        if (rawBytes == null) {
            return DiagnosticPrivacy.fromRestrictedValues(restricted);
        }
        for (int offset = 0;
                offset + RECORD_BYTES <= rawBytes.length;
                offset += TRANSPORT_RECORD_BYTES) {
            String record = new String(
                    rawBytes,
                    offset,
                    RECORD_BYTES,
                    StandardCharsets.ISO_8859_1);
            if (record.charAt(0) == 'A') {
                restricted.add(record.substring(29, 77));
            } else if (record.charAt(0) == 'B') {
                String taxTransport = record.substring(30, 44);
                String document = "1".equals(
                        record.substring(29, 30))
                        ? taxTransport.substring(3)
                        : taxTransport;
                String name = rightTrimSpaces(
                        record.substring(44, 84));
                String account = record.substring(92, 104);
                restricted.add(taxTransport);
                restricted.add(document);
                restricted.add(name);
                restricted.add(account);
                restricted.add(
                        record.substring(84, 87)
                                + ":"
                                + record.substring(87, 92)
                                + ":"
                                + account
                                + ":"
                                + record.substring(104, 105));
            }
        }
        return DiagnosticPrivacy.fromRestrictedValues(restricted);
    }

    private static List<String> restrictedValues(
            List<Settlement> settlements) {
        LinkedHashSet<String> values = new LinkedHashSet<>();
        for (Settlement settlement : settlements) {
            values.addAll(settlement.restrictedValues());
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

    private static boolean validCpf(String value) {
        if (!asciiDigits(value) || value.length() != 11
                || allDigitsEqual(value)) {
            return false;
        }
        int first = mod11Digit(
                value,
                9,
                new int[]{10, 9, 8, 7, 6, 5, 4, 3, 2});
        int second = mod11Digit(
                value.substring(0, 9) + first,
                10,
                new int[]{11, 10, 9, 8, 7, 6, 5, 4, 3, 2});
        return value.charAt(9) - '0' == first
                && value.charAt(10) - '0' == second;
    }

    private static boolean validCnpj(String value) {
        if (!asciiDigits(value) || value.length() != 14
                || allDigitsEqual(value)) {
            return false;
        }
        int first = mod11Digit(
                value,
                12,
                new int[]{5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2});
        int second = mod11Digit(
                value.substring(0, 12) + first,
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

    private static boolean allDigitsEqual(String value) {
        for (int index = 1; index < value.length(); index++) {
            if (value.charAt(index) != value.charAt(0)) {
                return false;
            }
        }
        return true;
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

    private static String rightTrimSpaces(String value) {
        int end = value.length();
        while (end > 0 && value.charAt(end - 1) == ' ') {
            end--;
        }
        return value.substring(0, end);
    }

    private static String padRight(String value, int length) {
        return value + " ".repeat(length - value.length());
    }

    private static String lastFour(String value) {
        return value.substring(value.length() - 4);
    }

    private static String isoDate(LocalDate value) {
        return value.toString();
    }

    private static String money(BigDecimal value) {
        return value.setScale(2).toPlainString();
    }

    private static BigDecimal sumSettlements(
            List<Settlement> values,
            MoneyFromSettlement mapper) {
        BigDecimal total = ZERO;
        for (Settlement value : values) {
            total = total.add(mapper.value(value));
        }
        return total;
    }

    private static BigDecimal sumLots(
            List<Lot> values,
            MoneyFromLot mapper) {
        BigDecimal total = ZERO;
        for (Lot value : values) {
            total = total.add(mapper.value(value));
        }
        return total;
    }

    @FunctionalInterface
    private interface MoneyFromSettlement {
        BigDecimal value(Settlement settlement);
    }

    @FunctionalInterface
    private interface MoneyFromLot {
        BigDecimal value(Lot lot);
    }

    record SourceDescriptor(
            String filename,
            String sha256,
            long sizeBytes) {
    }

    record TokenKeys(
            String paymentReferenceKey,
            String partyKey,
            String accountKey) {
    }

    private record PairSpan(
            int financialIndex,
            int beneficiaryIndex) {
    }

    private record LotSpan(
            int headerIndex,
            List<PairSpan> pairs,
            int trailerIndex) {
    }

    record Settlement(
            int recordNumberA,
            int recordNumberB,
            String lotNumberA,
            String sequenceA,
            String settlementIdA,
            String paymentReference,
            BigDecimal faceAmount,
            LocalDate dueDate,
            LocalDate paymentDate,
            BigDecimal discountAmount,
            BigDecimal feeAmount,
            String bankReference,
            String lotNumberB,
            String sequenceB,
            String settlementIdB,
            String taxIdType,
            String taxIdTransport,
            String beneficiaryName,
            String bankCode,
            String branchNumber,
            String accountNumber,
            String accountCheckDigit,
            String clientReference) {

        String document() {
            return "1".equals(taxIdType)
                    ? taxIdTransport.substring(3)
                    : taxIdTransport;
        }

        String canonicalAccount() {
            return bankCode
                    + ":"
                    + branchNumber
                    + ":"
                    + accountNumber
                    + ":"
                    + accountCheckDigit;
        }

        BigDecimal netAmount() {
            return faceAmount.subtract(discountAmount).add(feeAmount);
        }

        List<String> restrictedValues() {
            return List.of(
                    paymentReference,
                    beneficiaryName,
                    taxIdTransport,
                    document(),
                    canonicalAccount(),
                    accountNumber);
        }
    }

    record Lot(
            int recordNumber,
            String lotNumber,
            LocalDate settlementDate,
            String originatorId,
            List<Settlement> settlements,
            int declaredLogicalCount,
            BigDecimal declaredFaceAmount,
            BigDecimal declaredDiscountAmount,
            BigDecimal declaredFeeAmount,
            BigDecimal declaredNetAmount) {

        BigDecimal computedFaceAmount() {
            return sumSettlements(
                    settlements,
                    Settlement::faceAmount);
        }

        BigDecimal computedDiscountAmount() {
            return sumSettlements(
                    settlements,
                    Settlement::discountAmount);
        }

        BigDecimal computedFeeAmount() {
            return sumSettlements(
                    settlements,
                    Settlement::feeAmount);
        }

        BigDecimal computedNetAmount() {
            return sumSettlements(
                    settlements,
                    Settlement::netAmount);
        }
    }

    record ParsedBatch(
            String sourceFilename,
            String fileDateLexeme,
            LocalDate fileDate,
            String batchId,
            List<Lot> lots,
            List<Settlement> settlements,
            int declaredLotCount,
            int declaredPhysicalRecordCount,
            int declaredLogicalCount,
            BigDecimal declaredFaceAmount,
            BigDecimal declaredDiscountAmount,
            BigDecimal declaredFeeAmount,
            BigDecimal declaredNetAmount,
            int computedLotCount,
            int computedPhysicalRecordCount,
            int computedLogicalCount,
            BigDecimal computedFaceAmount,
            BigDecimal computedDiscountAmount,
            BigDecimal computedFeeAmount,
            BigDecimal computedNetAmount,
            int computedOrphanSegmentCount) {
    }

    record CsvOutput(
            byte[] bytes,
            int rowCount,
            BigDecimal faceAmount,
            BigDecimal discountAmount,
            BigDecimal feeAmount,
            BigDecimal netAmount,
            int orphanSegmentCount) {

        CsvOutput {
            bytes = bytes.clone();
        }

        @Override
        public byte[] bytes() {
            return bytes.clone();
        }
    }
}

package com.northwindpay.legacy.type05;

import com.fasterxml.jackson.databind.JsonNode;
import com.northwindpay.legacy.core.ArtifactIO;
import com.northwindpay.legacy.core.BatchProcessor;
import com.northwindpay.legacy.core.DiagnosticPrivacy;
import com.northwindpay.legacy.core.ProcessingContext;
import com.northwindpay.legacy.core.ProcessorException;
import com.northwindpay.legacy.core.ProcessorResult;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.text.Normalizer;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.time.format.ResolverStyle;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Contract-faithful Type 05 merchant-fee assessment converter.
 *
 * <p>The implementation keeps every validation phase explicit so an earlier
 * transport or grammar defect always wins over later business controls. It
 * uses strict UTF-8, exact {@link BigDecimal} arithmetic, a single-pass
 * quote-aware lexer, and manifest-last publication. No partial sanitized
 * bundle is published.
 */
public final class Type05Processor implements BatchProcessor {
    private static final int MAX_SOURCE_BYTES = 5_130_138;
    private static final int MAX_DETAIL_ROWS = 10_000;
    private static final int MAX_PHYSICAL_RECORD_BYTES = 512;
    private static final int MAX_CSV_BYTES = 10_000_000;
    private static final BigDecimal ZERO_MONEY =
            new BigDecimal("0.00");
    private static final BigDecimal MAX_RATE =
            new BigDecimal("100.000");
    private static final String SOURCE_HEADER = String.join(";",
            "assessment_id",
            "batch_id",
            "merchant_id",
            "merchant_tax_id",
            "fee_code",
            "description",
            "gross_amount_brl",
            "rate_percent",
            "assessed_fee_brl",
            "assessment_date");
    private static final String CSV_HEADER = String.join(",",
            "batch_id",
            "source_file",
            "source_record_number",
            "assessment_id",
            "merchant_id",
            "merchant_tax_id_masked",
            "fee_code",
            "description",
            "gross_amount_brl",
            "rate_percent",
            "assessed_fee_brl",
            "calculated_fee_brl",
            "assessment_date",
            "rounding_mode");
    private static final Pattern BATCH_PATTERN =
            Pattern.compile("B[0-9]{15}");
    private static final Pattern FILENAME_PATTERN = Pattern.compile(
            "NW_MERCHANT_FEES_([0-9]{8})_(B[0-9]{15})\\.csv");
    private static final Pattern ASSESSMENT_ID =
            Pattern.compile("FEE[0-9]{13}");
    private static final Pattern MERCHANT_ID =
            Pattern.compile("MER[0-9]{13}");
    private static final Pattern FEE_CODE =
            Pattern.compile("[A-Z][A-Z0-9_]{1,9}");
    private static final Pattern TAX_ID =
            Pattern.compile("[0-9]{14}");
    private static final Pattern SOURCE_MONEY =
            Pattern.compile("(?:0|[1-9][0-9]{0,11}),[0-9]{2}");
    private static final Pattern SOURCE_RATE =
            Pattern.compile("(?:0|[1-9][0-9]{0,2}),[0-9]{3}");
    private static final Pattern CONTROL_MONEY =
            Pattern.compile("(?:0|[1-9][0-9]{0,15})\\.[0-9]{2}");
    private static final Pattern LONG_DIGIT_RUN =
            Pattern.compile("[0-9]{11,}");
    private static final DateTimeFormatter SOURCE_DATE =
            DateTimeFormatter.ofPattern("dd/MM/uuuu", Locale.ROOT)
                    .withResolverStyle(ResolverStyle.STRICT);
    private static final DateTimeFormatter FILE_DATE =
            DateTimeFormatter.ofPattern("uuuuMMdd", Locale.ROOT)
                    .withResolverStyle(ResolverStyle.STRICT);
    private static final Set<Integer> BIDI_CONTROLS = Set.of(
            0x061c,
            0x200e,
            0x200f,
            0x202a,
            0x202b,
            0x202c,
            0x202d,
            0x202e,
            0x2066,
            0x2067,
            0x2068,
            0x2069);
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
            "size_bytes",
            "unicode_normalization");
    private static final Set<String> SOURCE_CONTROL_FIELDS = Set.of(
            "assessed_fee",
            "calculated_fee",
            "currency",
            "gross_amount",
            "row_count");

    @Override
    public String typeNumber() {
        return "05";
    }

    @Override
    public String typeCode() {
        return "MER_FEESET05";
    }

    @Override
    public String layoutVersion() {
        return "001";
    }

    /**
     * Validates, converts, and atomically publishes one Type 05 batch.
     *
     * @param context integrity-checked source and publication boundary
     * @return aggregate-only success evidence
     * @throws ProcessorException when any closed contract boundary fails
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
                        "Acquired source does not match Type 05 metadata");
            }

            ParsedBatch parsed = parseRaw(
                    rawBytes,
                    source.filename(),
                    context.batchId());
            validateSourceControls(parsed, context.sourceManifest());
            CsvOutput csv = renderCsv(parsed, source.filename());
            String csvFilename = source.filename().substring(
                    0,
                    source.filename().length() - ".csv".length())
                    + "_SANITIZED.csv";
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
            return ProcessorResult.type05Succeeded(
                    context.batchId(),
                    published.filename(),
                    published.sha256(),
                    csv.rowCount(),
                    money(csv.grossAmount()),
                    money(csv.assessedFee()),
                    money(csv.calculatedFee()));
        } catch (ProcessorException exception) {
            throw exception.withDiagnosticPrivacy(privacy);
        }
    }

    /**
     * Parses every raw-source rule through independent fee calculation.
     *
     * <p>Source-manifest controls remain a separate phase so a valid raw
     * observation can be compared independently with its source-owned
     * declarations.
     *
     * @param rawBytes exact source bytes
     * @param sourceFilename controlled raw filename
     * @param expectedBatchId manifest-selected batch
     * @return parsed assessments and independently computed controls
     * @throws ProcessorException on the first precedence-ordered defect
     */
    static ParsedBatch parseRaw(
            byte[] rawBytes,
            String sourceFilename,
            String expectedBatchId) throws ProcessorException {
        DiagnosticPrivacy privacy = diagnosticPrivacyForRaw(rawBytes);
        try {
            List<String> lines = physicalLines(rawBytes);
            if (!SOURCE_HEADER.equals(lines.get(0))) {
                throw new ProcessorException(
                        "INVALID_HEADER",
                        "Type 05 header is not exact");
            }

            List<LexedRow> rows = new ArrayList<>();
            for (int index = 1; index < lines.size(); index++) {
                rows.add(lexRow(lines.get(index), index + 1));
            }
            validateQuoting(rows);
            validateFieldCounts(rows);
            List<ParsedValues> values = validateLexicalFields(rows);
            validateDocuments(rows);
            validateIdentifiersAndDescriptions(rows);
            FilenameIdentity identity = validateBusinessIdentity(
                    rows,
                    sourceFilename,
                    expectedBatchId);
            validateAssessmentUniqueness(rows);

            List<Assessment> assessments = new ArrayList<>();
            BigDecimal grossSum = ZERO_MONEY;
            BigDecimal assessedSum = ZERO_MONEY;
            BigDecimal calculatedSum = ZERO_MONEY;
            for (ParsedValues parsed : values) {
                LexedRow row = parsed.row();
                BigDecimal calculated = parsed.gross()
                        .multiply(parsed.rate())
                        .movePointLeft(2)
                        .setScale(2, RoundingMode.HALF_UP);
                if (parsed.assessed().compareTo(calculated) != 0) {
                    throw rowFailure(
                            "FEE_CALCULATION_MISMATCH",
                            "Assessed fee differs from Type 05 HALF_UP result",
                            row.recordNumber());
                }
                LocalDate date = parseSourceDate(
                        row.fields().get(9),
                        row.recordNumber());
                assessments.add(new Assessment(
                        row.recordNumber(),
                        row.fields().get(0),
                        row.fields().get(1),
                        row.fields().get(2),
                        row.fields().get(3),
                        row.fields().get(4),
                        row.fields().get(5),
                        parsed.gross(),
                        parsed.rate(),
                        parsed.assessed(),
                        calculated,
                        date));
                grossSum = grossSum.add(parsed.gross());
                assessedSum = assessedSum.add(parsed.assessed());
                calculatedSum = calculatedSum.add(calculated);
            }
            return new ParsedBatch(
                    sourceFilename,
                    identity.fileDate(),
                    identity.batchId(),
                    List.copyOf(assessments),
                    assessments.size(),
                    grossSum,
                    assessedSum,
                    calculatedSum);
        } catch (ProcessorException exception) {
            throw exception.withDiagnosticPrivacy(privacy);
        }
    }

    /**
     * Compares source-owned controls with independent parsed controls in the
     * exact contract order.
     *
     * @param batch fully parsed raw source
     * @param manifest validated source manifest
     * @throws ProcessorException on the first aggregate mismatch
     */
    static void validateSourceControls(
            ParsedBatch batch,
            JsonNode manifest) throws ProcessorException {
        JsonNode controls = manifest.path("source_controls");
        if (!validControlObject(controls)) {
            throw invalidManifest();
        }
        DeclaredControls declared = declaredControls(controls);
        if (declared.rowCount() != batch.computedRowCount()) {
            throw controlFailure(
                    "SOURCE_CONTROL_COUNT_MISMATCH",
                    declared,
                    batch);
        }
        if (declared.grossAmount().compareTo(
                batch.computedGrossAmount()) != 0) {
            throw controlFailure(
                    "SOURCE_CONTROL_GROSS_MISMATCH",
                    declared,
                    batch);
        }
        if (declared.assessedFee().compareTo(
                batch.computedAssessedFee()) != 0) {
            throw controlFailure(
                    "SOURCE_CONTROL_ASSESSED_FEE_MISMATCH",
                    declared,
                    batch);
        }
        if (declared.calculatedFee().compareTo(
                batch.computedCalculatedFee()) != 0) {
            throw controlFailure(
                    "SOURCE_CONTROL_CALCULATED_FEE_MISMATCH",
                    declared,
                    batch);
        }
    }

    /**
     * Renders exact canonical UTF-8 comma CSV and performs the final
     * whole-output CNPJ scan.
     *
     * @param batch validated assessment batch
     * @param sourceFilename controlled raw filename
     * @return defensive candidate bytes and aggregate controls
     * @throws ProcessorException if output bounds or privacy fail
     */
    static CsvOutput renderCsv(
            ParsedBatch batch,
            String sourceFilename) throws ProcessorException {
        StringBuilder rendered = new StringBuilder(CSV_HEADER).append('\n');
        for (Assessment assessment : batch.assessments()) {
            appendCsvRow(rendered, List.of(
                    batch.batchId(),
                    sourceFilename,
                    Integer.toString(assessment.sourceRecordNumber()),
                    assessment.assessmentId(),
                    assessment.merchantId(),
                    maskCnpj(assessment.merchantTaxId()),
                    assessment.feeCode(),
                    assessment.description(),
                    money(assessment.grossAmount()),
                    rate(assessment.ratePercent()),
                    money(assessment.assessedFee()),
                    money(assessment.calculatedFee()),
                    assessment.assessmentDate().toString(),
                    "HALF_UP"));
        }
        byte[] bytes = rendered.toString().getBytes(StandardCharsets.UTF_8);
        if (bytes.length > MAX_CSV_BYTES) {
            throw new ProcessorException(
                    "INVALID_TRANSPORT",
                    "Sanitized Type 05 CSV exceeds its contract limit");
        }
        validatePrivacyBoundary(rendered, batch);
        return new CsvOutput(
                bytes,
                batch.computedRowCount(),
                batch.computedGrossAmount(),
                batch.computedAssessedFee(),
                batch.computedCalculatedFee());
    }

    private static List<String> physicalLines(byte[] rawBytes)
            throws ProcessorException {
        if (rawBytes == null || rawBytes.length > MAX_SOURCE_BYTES) {
            throw new ProcessorException(
                    "INVALID_SOURCE_SIZE",
                    "Type 05 source exceeds its contract size");
        }
        if (rawBytes.length >= 3
                && rawBytes[0] == (byte) 0xef
                && rawBytes[1] == (byte) 0xbb
                && rawBytes[2] == (byte) 0xbf) {
            throw new ProcessorException(
                    "INVALID_UTF8",
                    "Type 05 UTF-8 BOM is forbidden");
        }
        String decoded;
        try {
            decoded = StandardCharsets.UTF_8.newDecoder()
                    .onMalformedInput(CodingErrorAction.REPORT)
                    .onUnmappableCharacter(CodingErrorAction.REPORT)
                    .decode(ByteBuffer.wrap(rawBytes))
                    .toString();
        } catch (CharacterCodingException exception) {
            throw new ProcessorException(
                    "INVALID_UTF8",
                    "Type 05 source is not strict UTF-8",
                    exception);
        }
        if (!Normalizer.normalize(decoded, Normalizer.Form.NFC)
                .equals(decoded)) {
            throw new ProcessorException(
                    "INVALID_UNICODE_NORMALIZATION",
                    "Type 05 source is not already NFC");
        }
        if (rawBytes.length == 0
                || rawBytes[rawBytes.length - 1] != '\n'
                || (rawBytes.length > 1
                && rawBytes[rawBytes.length - 2] == '\n')) {
            throw new ProcessorException(
                    "INVALID_TRANSPORT",
                    "Type 05 source requires exactly one final LF");
        }
        for (byte value : rawBytes) {
            if (value == '\r') {
                throw new ProcessorException(
                        "INVALID_TRANSPORT",
                        "Type 05 source contains CR");
            }
        }

        List<Integer> byteLengths = new ArrayList<>();
        int start = 0;
        for (int index = 0; index < rawBytes.length; index++) {
            if (rawBytes[index] == '\n') {
                byteLengths.add(index - start);
                start = index + 1;
            }
        }
        if (byteLengths.size() < 2
                || byteLengths.size() > MAX_DETAIL_ROWS + 1
                || byteLengths.stream().anyMatch(length -> length == 0)) {
            throw new ProcessorException(
                    "INVALID_SOURCE_SIZE",
                    "Type 05 source has an invalid physical row count");
        }
        if (byteLengths.stream().anyMatch(
                length -> length > MAX_PHYSICAL_RECORD_BYTES)) {
            throw new ProcessorException(
                    "INVALID_RECORD_LENGTH",
                    "Type 05 physical record exceeds 512 bytes");
        }
        return List.of(decoded.substring(
                0,
                decoded.length() - 1).split("\\n", -1));
    }

    private static LexedRow lexRow(String line, int recordNumber)
            throws ProcessorException {
        List<String> fields = new ArrayList<>();
        List<Boolean> quoted = new ArrayList<>();
        int index = 0;
        while (true) {
            boolean isQuoted;
            String value;
            if (index < line.length() && line.charAt(index) == '"') {
                isQuoted = true;
                index++;
                StringBuilder characters = new StringBuilder();
                boolean closed = false;
                while (index < line.length()) {
                    char character = line.charAt(index);
                    if (character != '"') {
                        characters.append(character);
                        index++;
                    } else if (index + 1 < line.length()
                            && line.charAt(index + 1) == '"') {
                        characters.append('"');
                        index += 2;
                    } else {
                        index++;
                        closed = true;
                        break;
                    }
                }
                if (!closed
                        || (index < line.length()
                        && line.charAt(index) != ';')) {
                    throw rowFailure(
                            "INVALID_CSV_QUOTING",
                            "Type 05 contains malformed quoted CSV",
                            recordNumber);
                }
                value = characters.toString();
            } else {
                isQuoted = false;
                int fieldStart = index;
                while (index < line.length()
                        && line.charAt(index) != ';') {
                    if (line.charAt(index) == '"') {
                        throw rowFailure(
                                "INVALID_CSV_QUOTING",
                                "Type 05 contains a quote in an unquoted field",
                                recordNumber);
                    }
                    index++;
                }
                value = line.substring(fieldStart, index);
            }
            fields.add(value);
            quoted.add(isQuoted);
            if (index == line.length()) {
                break;
            }
            index++;
            if (index == line.length()) {
                fields.add("");
                quoted.add(false);
                break;
            }
        }
        return new LexedRow(
                recordNumber,
                List.copyOf(fields),
                List.copyOf(quoted));
    }

    private static void validateQuoting(List<LexedRow> rows)
            throws ProcessorException {
        for (LexedRow row : rows) {
            List<Boolean> quoted = row.quoted();
            if ((quoted.size() >= 6 && !quoted.get(5))
                    || hasQuotedNonDescription(quoted)) {
                throw rowFailure(
                        "INVALID_CSV_QUOTING",
                        "Type 05 field quote mode is not canonical",
                        row.recordNumber());
            }
        }
    }

    private static boolean hasQuotedNonDescription(
            List<Boolean> quoted) {
        for (int index = 0; index < quoted.size(); index++) {
            if (index != 5 && quoted.get(index)) {
                return true;
            }
        }
        return false;
    }

    private static void validateFieldCounts(List<LexedRow> rows)
            throws ProcessorException {
        for (LexedRow row : rows) {
            if (row.fields().size() != 10) {
                throw rowFailure(
                        "INVALID_FIELD_COUNT",
                        "Type 05 detail must contain exactly ten fields",
                        row.recordNumber());
            }
        }
    }

    private static List<ParsedValues> validateLexicalFields(
            List<LexedRow> rows) throws ProcessorException {
        List<ParsedValues> values = new ArrayList<>();
        for (LexedRow row : rows) {
            List<String> fields = row.fields();
            if (!TAX_ID.matcher(fields.get(3)).matches()
                    || !SOURCE_MONEY.matcher(fields.get(6)).matches()
                    || !SOURCE_RATE.matcher(fields.get(7)).matches()
                    || !SOURCE_MONEY.matcher(fields.get(8)).matches()) {
                throw rowFailure(
                        "INVALID_FIELD",
                        "Type 05 field lexeme is not canonical",
                        row.recordNumber());
            }
            BigDecimal gross = sourceDecimal(fields.get(6));
            BigDecimal rate = sourceDecimal(fields.get(7));
            BigDecimal assessed = sourceDecimal(fields.get(8));
            if (gross.compareTo(BigDecimal.ZERO) <= 0
                    || rate.compareTo(BigDecimal.ZERO) <= 0
                    || rate.compareTo(MAX_RATE) > 0
                    || assessed.compareTo(BigDecimal.ZERO) < 0) {
                throw rowFailure(
                        "INVALID_FIELD",
                        "Type 05 decimal is outside contract bounds",
                        row.recordNumber());
            }
            values.add(new ParsedValues(
                    row,
                    gross,
                    rate,
                    assessed));
        }
        return values;
    }

    private static void validateDocuments(List<LexedRow> rows)
            throws ProcessorException {
        for (LexedRow row : rows) {
            if (!validCnpj(row.fields().get(3))) {
                throw rowFailure(
                        "INVALID_DOCUMENT",
                        "Type 05 CNPJ check digits are invalid",
                        row.recordNumber());
            }
        }
    }

    private static void validateIdentifiersAndDescriptions(
            List<LexedRow> rows) throws ProcessorException {
        Set<String> rawTaxIds = new HashSet<>();
        for (LexedRow row : rows) {
            rawTaxIds.add(row.fields().get(3));
        }
        for (LexedRow row : rows) {
            List<String> fields = row.fields();
            if (!ASSESSMENT_ID.matcher(fields.get(0)).matches()
                    || !BATCH_PATTERN.matcher(fields.get(1)).matches()
                    || !MERCHANT_ID.matcher(fields.get(2)).matches()
                    || !FEE_CODE.matcher(fields.get(4)).matches()) {
                throw rowFailure(
                        "INVALID_IDENTIFIER",
                        "Type 05 identifier is not canonical",
                        row.recordNumber());
            }
            if (!safeDescription(fields.get(5), rawTaxIds)) {
                throw rowFailure(
                        "INVALID_DESCRIPTION",
                        "Type 05 description is unsafe",
                        row.recordNumber());
            }
        }
    }

    private static FilenameIdentity validateBusinessIdentity(
            List<LexedRow> rows,
            String sourceFilename,
            String expectedBatchId) throws ProcessorException {
        Matcher filename = FILENAME_PATTERN.matcher(sourceFilename);
        if (!filename.matches()
                || !filename.group(2).equals(expectedBatchId)) {
            throw new ProcessorException(
                    "INVALID_BUSINESS_DATE",
                    "Type 05 filename identity is invalid");
        }
        LocalDate filenameDate;
        try {
            filenameDate = LocalDate.parse(filename.group(1), FILE_DATE);
        } catch (DateTimeParseException exception) {
            throw new ProcessorException(
                    "INVALID_BUSINESS_DATE",
                    "Type 05 filename date is invalid");
        }
        for (LexedRow row : rows) {
            LocalDate sourceDate = parseSourceDate(
                    row.fields().get(9),
                    row.recordNumber());
            if (!row.fields().get(1).equals(filename.group(2))
                    || !sourceDate.equals(filenameDate)) {
                throw rowFailure(
                        "INVALID_BUSINESS_DATE",
                        "Type 05 row does not match filename identity",
                        row.recordNumber());
            }
        }
        return new FilenameIdentity(
                filename.group(1),
                filename.group(2));
    }

    private static LocalDate parseSourceDate(
            String value,
            int recordNumber) throws ProcessorException {
        try {
            LocalDate parsed = LocalDate.parse(value, SOURCE_DATE);
            if (!SOURCE_DATE.format(parsed).equals(value)) {
                throw new DateTimeParseException(
                        "Noncanonical date",
                        value,
                        0);
            }
            return parsed;
        } catch (DateTimeParseException exception) {
            throw rowFailure(
                    "INVALID_BUSINESS_DATE",
                    "Type 05 assessment date is invalid",
                    recordNumber);
        }
    }

    private static void validateAssessmentUniqueness(
            List<LexedRow> rows) throws ProcessorException {
        Set<String> seen = new HashSet<>();
        for (LexedRow row : rows) {
            if (!seen.add(row.fields().get(0))) {
                throw rowFailure(
                        "DUPLICATE_IDENTIFIER",
                        "Type 05 assessment ID is duplicated",
                        row.recordNumber());
            }
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
                || !"05".equals(fileType.path("number").asText())
                || !fileType.path("code").isTextual()
                || !"MER_FEESET05".equals(
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
                || sizeBytes < 1
                || sizeBytes > MAX_SOURCE_BYTES
                || !sourceFile.path("encoding").isTextual()
                || !"UTF-8".equals(sourceFile.path("encoding").asText())
                || !sourceFile.path("line_ending").isTextual()
                || !"LF".equals(sourceFile.path("line_ending").asText())
                || !sourceFile.path("final_newline").isTextual()
                || !"required".equals(
                        sourceFile.path("final_newline").asText())
                || !sourceFile.path("unicode_normalization").isTextual()
                || !"NFC".equals(
                        sourceFile.path("unicode_normalization").asText())
                || !validControlObject(
                        manifest.path("source_controls"))) {
            throw invalidManifest();
        }
        return new SourceDescriptor(filename, sha256, sizeBytes);
    }

    private static boolean validControlObject(JsonNode controls) {
        if (!hasExactFields(controls, SOURCE_CONTROL_FIELDS)
                || !controls.path("currency").isTextual()
                || !"BRL".equals(controls.path("currency").asText())
                || !controls.path("row_count").isIntegralNumber()
                || !controls.path("row_count").canConvertToInt()) {
            return false;
        }
        int count = controls.path("row_count").intValue();
        if (count < 1 || count > MAX_DETAIL_ROWS) {
            return false;
        }
        String gross = textual(controls, "gross_amount");
        String assessed = textual(controls, "assessed_fee");
        String calculated = textual(controls, "calculated_fee");
        return gross != null
                && assessed != null
                && calculated != null
                && CONTROL_MONEY.matcher(gross).matches()
                && CONTROL_MONEY.matcher(assessed).matches()
                && CONTROL_MONEY.matcher(calculated).matches()
                && new BigDecimal(gross).compareTo(BigDecimal.ZERO) > 0;
    }

    private static DeclaredControls declaredControls(JsonNode controls) {
        return new DeclaredControls(
                controls.path("row_count").intValue(),
                new BigDecimal(controls.path("gross_amount").asText()),
                new BigDecimal(controls.path("assessed_fee").asText()),
                new BigDecimal(controls.path("calculated_fee").asText()));
    }

    private static ProcessorException controlFailure(
            String code,
            DeclaredControls declared,
            ParsedBatch batch) {
        return ProcessorException.type05SourceControlMismatch(
                code,
                declared.rowCount(),
                money(declared.grossAmount()),
                money(declared.assessedFee()),
                money(declared.calculatedFee()),
                batch.computedRowCount(),
                money(batch.computedGrossAmount()),
                money(batch.computedAssessedFee()),
                money(batch.computedCalculatedFee()));
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
                "size_bytes", output.bytes().length,
                "unicode_normalization", "NFC");
        Map<String, Object> fileType = Map.of(
                "code", "MER_FEESET05",
                "contract_version", 1,
                "layout_version", "001",
                "number", "05");
        Map<String, Object> lineage = Map.of(
                "manifest_sha256",
                ArtifactIO.sha256(context.sourceManifestBytes()),
                "raw_file", source.filename(),
                "raw_sha256", source.sha256());
        Map<String, Object> controls = Map.of(
                "assessed_fee", money(output.assessedFee()),
                "calculated_fee", money(output.calculatedFee()),
                "currency", "BRL",
                "gross_amount", money(output.grossAmount()),
                "row_count", output.rowCount());
        return Map.of(
                "batch_id", context.batchId(),
                "csv_file", csvFile,
                "file_type", fileType,
                "schema_version", 1,
                "source_lineage", lineage,
                "stage_controls", controls);
    }

    private static boolean safeDescription(
            String value,
            Set<String> rawTaxIds) {
        int length = value.codePointCount(0, value.length());
        if (length < 1 || length > 80) {
            return false;
        }
        int first = value.codePointAt(0);
        if (first == '=' || first == '+'
                || first == '-' || first == '@') {
            return false;
        }
        if (LONG_DIGIT_RUN.matcher(value).find()) {
            return false;
        }
        for (int index = 0; index < value.length();) {
            int codePoint = value.codePointAt(index);
            if (Character.getType(codePoint) == Character.CONTROL
                    || BIDI_CONTROLS.contains(codePoint)) {
                return false;
            }
            index += Character.charCount(codePoint);
        }
        for (String taxId : rawTaxIds) {
            if (value.contains(taxId)) {
                return false;
            }
        }
        return true;
    }

    private static boolean validCnpj(String value) {
        if (!TAX_ID.matcher(value).matches()) {
            return false;
        }
        boolean repeated = true;
        for (int index = 1; index < value.length(); index++) {
            if (value.charAt(index) != value.charAt(0)) {
                repeated = false;
                break;
            }
        }
        if (repeated) {
            return false;
        }
        int first = cnpjDigit(value.substring(0, 12),
                new int[]{5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2});
        int second = cnpjDigit(value.substring(0, 12) + first,
                new int[]{6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2});
        return value.charAt(12) - '0' == first
                && value.charAt(13) - '0' == second;
    }

    private static int cnpjDigit(String digits, int[] weights) {
        int total = 0;
        for (int index = 0; index < weights.length; index++) {
            total += (digits.charAt(index) - '0') * weights[index];
        }
        int remainder = total % 11;
        return remainder < 2 ? 0 : 11 - remainder;
    }

    private static void validatePrivacyBoundary(
            CharSequence csv,
            ParsedBatch batch) throws ProcessorException {
        String output = csv.toString();
        for (Assessment assessment : batch.assessments()) {
            if (output.contains(assessment.merchantTaxId())) {
                throw rowFailure(
                        "PRIVACY_OUTPUT_VIOLATION",
                        "Sanitized Type 05 CSV contains a raw CNPJ",
                        assessment.sourceRecordNumber());
            }
        }
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
        if (value.indexOf(',') < 0
                && value.indexOf('"') < 0
                && value.indexOf('\r') < 0
                && value.indexOf('\n') < 0) {
            return value;
        }
        return "\"" + value.replace("\"", "\"\"") + "\"";
    }

    private static String maskCnpj(String value) {
        return "**********" + value.substring(10);
    }

    private static BigDecimal sourceDecimal(String value) {
        return new BigDecimal(value.replace(',', '.'));
    }

    private static String money(BigDecimal value) {
        return value.setScale(2).toPlainString();
    }

    private static String rate(BigDecimal value) {
        return value.setScale(3).toPlainString();
    }

    private static String textual(JsonNode object, String field) {
        JsonNode value = object.path(field);
        return value.isTextual() ? value.asText() : null;
    }

    private static boolean hasExactFields(
            JsonNode object,
            Set<String> expected) {
        if (!object.isObject() || object.size() != expected.size()) {
            return false;
        }
        Set<String> actual = new HashSet<>();
        Iterator<String> names = object.fieldNames();
        names.forEachRemaining(actual::add);
        return actual.equals(expected);
    }

    private static ProcessorException rowFailure(
            String code,
            String message,
            int recordNumber) {
        return new ProcessorException(
                code,
                message,
                recordNumber,
                null);
    }

    private static ProcessorException invalidManifest() {
        return new ProcessorException(
                "INVALID_MANIFEST",
                "Source manifest does not match Type 05");
    }

    private static DiagnosticPrivacy diagnosticPrivacyForRaw(
            byte[] rawBytes) {
        if (rawBytes == null) {
            return DiagnosticPrivacy.fromRestrictedValues(List.of());
        }
        List<String> restricted = new ArrayList<>();
        String text = new String(rawBytes, StandardCharsets.ISO_8859_1);
        String[] lines = text.split("\\n", -1);
        for (int index = 1; index < lines.length; index++) {
            String[] fields = lines[index].split(";", 5);
            if (fields.length >= 4
                    && TAX_ID.matcher(fields[3]).matches()) {
                restricted.add(fields[3]);
            }
        }
        return DiagnosticPrivacy.fromRestrictedValues(restricted);
    }

    /**
     * Controlled source identity from the validated manifest.
     */
    record SourceDescriptor(
            String filename,
            String sha256,
            long sizeBytes) {
    }

    /**
     * One quote-aware raw detail row.
     */
    record LexedRow(
            int recordNumber,
            List<String> fields,
            List<Boolean> quoted) {
    }

    private record ParsedValues(
            LexedRow row,
            BigDecimal gross,
            BigDecimal rate,
            BigDecimal assessed) {
    }

    private record FilenameIdentity(
            String fileDate,
            String batchId) {
    }

    private record DeclaredControls(
            int rowCount,
            BigDecimal grossAmount,
            BigDecimal assessedFee,
            BigDecimal calculatedFee) {
    }

    /**
     * Validated merchant assessment. The raw CNPJ and description remain
     * inside the conversion boundary and are never attached to diagnostics.
     */
    record Assessment(
            int sourceRecordNumber,
            String assessmentId,
            String batchId,
            String merchantId,
            String merchantTaxId,
            String feeCode,
            String description,
            BigDecimal grossAmount,
            BigDecimal ratePercent,
            BigDecimal assessedFee,
            BigDecimal calculatedFee,
            LocalDate assessmentDate) {
    }

    /**
     * Fully parsed Type 05 batch and its independent controls.
     */
    record ParsedBatch(
            String sourceFilename,
            String fileDate,
            String batchId,
            List<Assessment> assessments,
            int computedRowCount,
            BigDecimal computedGrossAmount,
            BigDecimal computedAssessedFee,
            BigDecimal computedCalculatedFee) {
    }

    /**
     * Candidate sanitized bytes and publication controls.
     */
    record CsvOutput(
            byte[] bytes,
            int rowCount,
            BigDecimal grossAmount,
            BigDecimal assessedFee,
            BigDecimal calculatedFee) {

        CsvOutput {
            bytes = bytes.clone();
        }

        @Override
        public byte[] bytes() {
            return bytes.clone();
        }
    }
}

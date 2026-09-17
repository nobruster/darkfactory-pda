package com.northwindpay.legacy.core;

import com.fasterxml.jackson.databind.JsonNode;
import com.northwindpay.legacy.type01.Type01Processor;
import com.northwindpay.legacy.type02.Type02Processor;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class ProcessorDispatcherTest {
    private static final String DOCUMENT_KEY =
            "northwind-pay-edp-fixture-document-key-v1";

    @Test
    void legacyInvocationStillDispatchesType01ByteForByte(
            @TempDir Path workingDirectory) throws Exception {
        String batchId = "B202607230000001";
        String sourceFilename =
                "NW_CARD_SETTLEMENT_20260723_"
                        + batchId
                        + ".dat";
        byte[] raw = Files.readAllBytes(
                type01FixtureRoot().resolve("valid-minimal.dat"));
        byte[] manifest = StableJson.bytes(Map.of(
                "batch_id", batchId,
                "file_type", Map.of(
                        "code", "CRD_SETTLE01",
                        "contract_version", 1,
                        "layout_version", "001",
                        "number", "01"),
                "schema_version", 1,
                "source_controls", Map.of(
                        "currency", "BRL",
                        "detail_count", 2,
                        "net_amount", "173.45"),
                "source_file", Map.of(
                        "encoding", "ISO-8859-1",
                        "final_newline", "required",
                        "line_ending", "LF",
                        "name", sourceFilename,
                        "sha256", ArtifactIO.sha256(raw),
                        "size_bytes", raw.length)));
        FakeArtifactGateway gateway = gateway(
                batchId,
                sourceFilename,
                raw,
                manifest);

        ProcessorResult result = new ProcessorDispatcher(
                List.of(
                        new Type01Processor(),
                        new Type02Processor()))
                .dispatch(
                        batchId,
                        null,
                        configuration(),
                        gateway,
                        workingDirectory);

        assertEquals("succeeded", result.asMap().get("status"));
        assertEquals(
                "a7db2ed1bfe76ab180bba750bbd4d79184d1e118b643a2a0e4d6f0e7f6ec089d",
                result.asMap().get("csv_sha256"));
        assertArrayEquals(
                Files.readAllBytes(
                        type01FixtureRoot().resolve(
                                "expected-sanitized.csv")),
                gateway.published.get(
                        sourceFilename.replace(".dat", ".csv")));
    }

    @Test
    void manifestDispatchRunsCompleteType02ArtifactBoundary(
            @TempDir Path workingDirectory) throws Exception {
        String batchId = "B202607230000101";
        String sourceFilename = filename(batchId);
        byte[] raw = Files.readAllBytes(
                fixtureRoot().resolve("valid-minimal.txt"));
        FakeArtifactGateway gateway = gateway(
                batchId,
                sourceFilename,
                raw,
                sourceManifest(
                        batchId,
                        sourceFilename,
                        raw,
                        2,
                        "200.00",
                        "26.55",
                        "173.45"));
        ProcessorDispatcher dispatcher =
                new ProcessorDispatcher(
                        List.of(new Type02Processor()));

        ProcessorResult result = dispatcher.dispatch(
                batchId,
                "02",
                configuration(),
                gateway,
                workingDirectory);

        assertEquals(
                "succeeded",
                result.asMap().get("status"));
        assertEquals(
                "8bd2e4bdb2d7fbea367d5105edae3ff0a56fac091ea9b1072af0821a8e25a20a",
                result.asMap().get("csv_sha256"));
        assertEquals(
                "/csv/outgoing/" + batchId,
                gateway.publishedDirectory);
        assertEquals(
                "sanitized-manifest.json",
                gateway.readinessManifest);
        assertEquals(
                List.of(
                        sourceFilename.replace(".txt", ".csv"),
                        sourceFilename.replace(".txt", ".csv.sha256"),
                        "sanitized-manifest.json"),
                gateway.published.keySet().stream().toList());
        assertArrayEquals(
                Files.readAllBytes(
                        fixtureRoot().resolve(
                                "expected-sanitized.csv")),
                gateway.published.get(
                        sourceFilename.replace(".txt", ".csv")));

        JsonNode sanitized = StableJson.parse(
                gateway.published.get("sanitized-manifest.json"));
        assertEquals(
                "02",
                sanitized.path("file_type").path("number").asText());
        assertEquals(
                2,
                sanitized.path("stage_controls").path(
                        "row_count").asInt());
        assertEquals(
                "200.00",
                sanitized.path("stage_controls").path(
                        "credit_amount").asText());
        assertEquals(
                "26.55",
                sanitized.path("stage_controls").path(
                        "debit_amount").asText());
        assertEquals(
                "173.45",
                sanitized.path("stage_controls").path(
                        "net_amount").asText());
        assertEquals(
                1,
                sanitized.path("stage_controls").path(
                        "returned_count").asInt());
    }

    @Test
    void explicitTypeAssertionCannotOverrideManifestSelection(
            @TempDir Path workingDirectory) throws Exception {
        String batchId = "B202607230000101";
        String sourceFilename = filename(batchId);
        byte[] raw = Files.readAllBytes(
                fixtureRoot().resolve("valid-minimal.txt"));
        FakeArtifactGateway gateway = gateway(
                batchId,
                sourceFilename,
                raw,
                sourceManifest(
                        batchId,
                        sourceFilename,
                        raw,
                        2,
                        "200.00",
                        "26.55",
                        "173.45"));

        ProcessorException exception = assertThrows(
                ProcessorException.class,
                () -> new ProcessorDispatcher(
                        List.of(new Type02Processor()))
                        .dispatch(
                                batchId,
                                "01",
                                configuration(),
                                gateway,
                                workingDirectory));

        assertEquals(
                "PROCESSOR_SELECTION_MISMATCH",
                exception.code());
        assertEquals("02", exception.typeNumber());
        assertTrue(gateway.published.isEmpty());
    }

    @Test
    void darkFactoryFailurePublishesNoSanitizedArtifact(
            @TempDir Path workingDirectory) throws Exception {
        String batchId = "B202607230000105";
        String sourceFilename = filename(batchId);
        byte[] raw = Files.readAllBytes(
                fixtureRoot().resolve("df-source-002.txt"));
        FakeArtifactGateway gateway = gateway(
                batchId,
                sourceFilename,
                raw,
                sourceManifest(
                        batchId,
                        sourceFilename,
                        raw,
                        2,
                        "200.00",
                        "26.55",
                        "173.44"));

        ProcessorException exception = assertThrows(
                ProcessorException.class,
                () -> new ProcessorDispatcher(
                        List.of(new Type02Processor()))
                        .dispatch(
                                batchId,
                                null,
                                configuration(),
                                gateway,
                                workingDirectory));

        assertEquals(
                "SOURCE_CONTROL_NET_MISMATCH",
                exception.code());
        assertEquals("02", exception.typeNumber());
        assertTrue(gateway.published.isEmpty());
        assertFalse(Files.exists(
                workingDirectory.resolve(
                        sourceFilename.replace(".txt", ".csv"))));
    }

    @Test
    void sourceIntegrityFailureStopsBeforeTypedParsing(
            @TempDir Path workingDirectory) throws Exception {
        String batchId = "B202607230000101";
        String sourceFilename = filename(batchId);
        byte[] approved = Files.readAllBytes(
                fixtureRoot().resolve("valid-minimal.txt"));
        byte[] tampered = approved.clone();
        tampered[20] ^= 1;
        FakeArtifactGateway gateway = gateway(
                batchId,
                sourceFilename,
                tampered,
                sourceManifest(
                        batchId,
                        sourceFilename,
                        approved,
                        2,
                        "200.00",
                        "26.55",
                        "173.45"));

        ProcessorException exception = assertThrows(
                ProcessorException.class,
                () -> new ProcessorDispatcher(
                        List.of(new Type02Processor()))
                        .dispatch(
                                batchId,
                                "02",
                                configuration(),
                                gateway,
                                workingDirectory));

        assertEquals("SOURCE_INTEGRITY_ERROR", exception.code());
        assertTrue(gateway.published.isEmpty());
    }

    @Test
    void duplicateRegistryEntryFailsAtStartup() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new ProcessorDispatcher(List.of(
                        new Type02Processor(),
                        new Type02Processor())));
    }

    @Test
    void configurationStringNeverSerializesSecrets() {
        Configuration configuration = configuration();
        String rendered = configuration.toString();

        assertFalse(rendered.contains(DOCUMENT_KEY));
        assertFalse(rendered.contains(
                "northwind-pay-edp-fixture-key-v1"));
        assertTrue(rendered.contains("<redacted>"));
    }

    @Test
    void configurationKeepsTypeSpecificKeyDomainsIndependent()
            throws Exception {
        Configuration configuration = Configuration.fromEnvironment(
                Map.of(
                        "SFTP_HOST", "sftp",
                        "SFTP_PORT", "22",
                        "SFTP_PROCESSOR_USER", "processor",
                        "SFTP_PROCESSOR_PASSWORD", "password",
                        "SFTP_KNOWN_HOSTS", "/known_hosts",
                        "NWP_DOCUMENT_TOKEN_KEY", DOCUMENT_KEY));

        assertEquals(DOCUMENT_KEY, configuration.documentTokenKey());
        assertNull(configuration.tokenizationKey());
    }

    @Test
    void manifestJsonRejectsAmbiguousDuplicateKeys() {
        ProcessorException exception = assertThrows(
                ProcessorException.class,
                () -> StableJson.parse(
                        "{\"batch_id\":\"a\",\"batch_id\":\"b\"}"
                                .getBytes(StandardCharsets.UTF_8)));

        assertEquals("INVALID_MANIFEST", exception.code());
    }

    private static FakeArtifactGateway gateway(
            String batchId,
            String sourceFilename,
            byte[] raw,
            byte[] manifest) {
        String directory = "/raw/processing/" + batchId;
        LinkedHashMap<String, byte[]> downloads =
                new LinkedHashMap<>();
        downloads.put(
                directory + "/source-manifest.json",
                manifest);
        downloads.put(
                directory + "/" + sourceFilename,
                raw);
        downloads.put(
                directory + "/" + sourceFilename + ".sha256",
                (ArtifactIO.sha256(raw)
                        + "  "
                        + sourceFilename
                        + "\n").getBytes(StandardCharsets.US_ASCII));
        return new FakeArtifactGateway(downloads);
    }

    private static byte[] sourceManifest(
            String batchId,
            String sourceFilename,
            byte[] raw,
            int eventCount,
            String credit,
            String debit,
            String net) throws ProcessorException {
        return StableJson.bytes(Map.of(
                "batch_id", batchId,
                "file_type", Map.of(
                        "code", "PIX_EVENTS01",
                        "contract_version", 1,
                        "layout_version", "001",
                        "number", "02"),
                "schema_version", 1,
                "source_controls", Map.of(
                        "credit_amount", credit,
                        "currency", "BRL",
                        "debit_amount", debit,
                        "event_count", eventCount,
                        "net_amount", net),
                "source_file", Map.of(
                        "encoding", "UTF-8",
                        "final_newline", "required",
                        "line_ending", "LF",
                        "name", sourceFilename,
                        "sha256", ArtifactIO.sha256(raw),
                        "size_bytes", raw.length)));
    }

    private static Configuration configuration() {
        return new Configuration(
                "unused",
                22,
                "unused",
                "unused",
                Path.of("unused"),
                "northwind-pay-edp-fixture-key-v1",
                DOCUMENT_KEY);
    }

    private static String filename(String batchId) {
        return "NW_INSTANT_PAYMENT_"
                + batchId.substring(1, 9)
                + "_"
                + batchId
                + ".txt";
    }

    private static Path fixtureRoot() {
        return Path.of(System.getProperty(
                "contract.type02.fixture.root",
                "../../contracts/types/02-instant-payment-events/main"))
                .toAbsolutePath()
                .normalize();
    }

    private static Path type01FixtureRoot() {
        return Path.of(System.getProperty(
                "contract.fixture.root",
                "../../contracts/types/01-card-settlement/main"))
                .toAbsolutePath()
                .normalize();
    }

    private static final class FakeArtifactGateway
            implements ArtifactGateway {
        private final Map<String, byte[]> downloads;
        private final LinkedHashMap<String, byte[]> published =
                new LinkedHashMap<>();
        private String publishedDirectory;
        private String readinessManifest;

        private FakeArtifactGateway(Map<String, byte[]> downloads) {
            this.downloads = Map.copyOf(downloads);
        }

        @Override
        public void download(String remotePath, Path localPath)
                throws ProcessorException {
            byte[] content = downloads.get(remotePath);
            if (content == null) {
                throw new ProcessorException(
                        "SFTP_DOWNLOAD_ERROR",
                        "Missing fake source artifact");
            }
            try {
                Files.write(localPath, content);
            } catch (java.io.IOException exception) {
                throw new ProcessorException(
                        "LOCAL_IO_ERROR",
                        "Cannot write fake source artifact",
                        exception);
            }
        }

        @Override
        public void publish(
                String remoteDirectory,
                LinkedHashMap<String, Path> artifacts,
                String readiness) throws ProcessorException {
            publishedDirectory = remoteDirectory;
            readinessManifest = readiness;
            try {
                for (Map.Entry<String, Path> artifact
                        : artifacts.entrySet()) {
                    published.put(
                            artifact.getKey(),
                            Files.readAllBytes(artifact.getValue()));
                }
            } catch (java.io.IOException exception) {
                throw new ProcessorException(
                        "LOCAL_IO_ERROR",
                        "Cannot read fake sanitized artifact",
                        exception);
            }
        }

        @Override
        public void close() {
            // No remote resources.
        }
    }
}

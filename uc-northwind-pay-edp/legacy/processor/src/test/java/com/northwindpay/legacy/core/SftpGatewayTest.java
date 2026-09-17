package com.northwindpay.legacy.core;

import com.jcraft.jsch.ChannelSftp;
import com.jcraft.jsch.SftpException;
import org.junit.jupiter.api.Test;

import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class SftpGatewayTest {
    private static final String REMOTE =
            "/csv/outgoing/B202607230000001";

    @Test
    void failedReadinessRenameRemovesPartsFinalsAndNewDirectory() {
        FakePublicationOperations operations =
                new FakePublicationOperations();
        operations.failReadinessRename = true;

        ProcessorException exception = assertThrows(
                ProcessorException.class,
                () -> SftpGateway.publishArtifacts(
                        operations,
                        REMOTE,
                        artifacts(),
                        "sanitized-manifest.json"));

        assertEquals("SFTP_PUBLICATION_ERROR", exception.code());
        assertFalse(operations.directories.contains(REMOTE));
        assertFalse(
                operations.files.stream()
                        .anyMatch(path -> path.startsWith(REMOTE + "/")));
    }

    @Test
    void existingImmutableBatchDirectoryIsRejectedWithoutMutation() {
        FakePublicationOperations operations =
                new FakePublicationOperations();
        operations.directories.add(REMOTE);
        String existing = REMOTE + "/existing-safe-marker";
        operations.files.add(existing);

        ProcessorException exception = assertThrows(
                ProcessorException.class,
                () -> SftpGateway.publishArtifacts(
                        operations,
                        REMOTE,
                        artifacts(),
                        "sanitized-manifest.json"));

        assertEquals("SFTP_PUBLICATION_ERROR", exception.code());
        assertTrue(operations.directories.contains(REMOTE));
        assertEquals(Set.of(existing), operations.files);
    }

    @Test
    void successfulPublicationRenamesReadinessManifestLast() throws Exception {
        FakePublicationOperations operations =
                new FakePublicationOperations();

        SftpGateway.publishArtifacts(
                operations,
                REMOTE,
                artifacts(),
                "sanitized-manifest.json");

        assertEquals(
                REMOTE + "/sanitized-manifest.json",
                operations.renameTargets.getLast());
        assertTrue(
                operations.files.contains(
                        REMOTE + "/sanitized-manifest.json"));
        assertFalse(
                operations.files.stream().anyMatch(path -> path.endsWith(".part")));
    }

    private static LinkedHashMap<String, Path> artifacts() {
        LinkedHashMap<String, Path> artifacts = new LinkedHashMap<>();
        artifacts.put("batch.csv", Path.of("batch.csv"));
        artifacts.put("batch.csv.sha256", Path.of("batch.csv.sha256"));
        artifacts.put(
                "sanitized-manifest.json",
                Path.of("sanitized-manifest.json"));
        return artifacts;
    }

    private static final class FakePublicationOperations
            implements SftpGateway.PublicationOperations {
        private final Set<String> directories = new HashSet<>();
        private final Set<String> files = new HashSet<>();
        private final List<String> renameTargets = new ArrayList<>();
        private boolean failReadinessRename;

        @Override
        public boolean exists(String path) {
            return directories.contains(path);
        }

        @Override
        public void makeDirectory(String path) {
            directories.add(path);
        }

        @Override
        public void chmod(String path, int permissions) {
            // Permissions are enforced by the real SFTP adapter.
        }

        @Override
        public void upload(Path localPath, String remotePath) {
            files.add(remotePath);
        }

        @Override
        public void rename(String source, String target)
                throws SftpException {
            if (failReadinessRename
                    && target.endsWith("/sanitized-manifest.json")) {
                throw failure("injected readiness rename failure");
            }
            if (!files.remove(source)) {
                throw failure("missing rename source");
            }
            files.add(target);
            renameTargets.add(target);
        }

        @Override
        public void remove(String path) throws SftpException {
            if (!files.remove(path)) {
                throw failure("missing file");
            }
        }

        @Override
        public void removeDirectory(String path) throws SftpException {
            if (files.stream().anyMatch(
                    file -> file.startsWith(path + "/"))) {
                throw failure("directory is not empty");
            }
            if (!directories.remove(path)) {
                throw failure("missing directory");
            }
        }

        private static SftpException failure(String message) {
            return new SftpException(
                    ChannelSftp.SSH_FX_FAILURE,
                    message);
        }
    }
}

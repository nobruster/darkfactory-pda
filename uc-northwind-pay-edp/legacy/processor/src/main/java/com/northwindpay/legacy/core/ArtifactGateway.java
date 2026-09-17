package com.northwindpay.legacy.core;

import java.nio.file.Path;
import java.util.LinkedHashMap;

/**
 * Narrow remote-artifact port used by acquisition and publication.
 *
 * <p>The production adapter is SFTP; tests can provide an in-memory adapter
 * without weakening the production transport policy.
 */
public interface ArtifactGateway extends AutoCloseable {
    /**
     * Downloads one remote artifact into the private working directory.
     */
    void download(String remotePath, Path localPath)
            throws ProcessorException;

    /**
     * Atomically publishes a set whose readiness manifest becomes visible
     * last.
     */
    void publish(
            String remoteDirectory,
            LinkedHashMap<String, Path> artifacts,
            String readinessManifest) throws ProcessorException;

    @Override
    void close();
}

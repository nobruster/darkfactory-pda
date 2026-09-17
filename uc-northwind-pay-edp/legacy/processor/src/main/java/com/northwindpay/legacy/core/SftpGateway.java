package com.northwindpay.legacy.core;

import com.jcraft.jsch.ChannelSftp;
import com.jcraft.jsch.JSch;
import com.jcraft.jsch.JSchException;
import com.jcraft.jsch.Session;
import com.jcraft.jsch.SftpException;

import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Strict-host-key SFTP boundary shared by all legacy processors.
 *
 * <p>Sanitized publications use temporary names and rename the readiness
 * manifest last. Consumers therefore cannot observe a partially ready batch.
 */
public final class SftpGateway implements ArtifactGateway {
    private final Session session;
    private final ChannelSftp channel;

    private SftpGateway(Session session, ChannelSftp channel) {
        this.session = session;
        this.channel = channel;
    }

    public static SftpGateway connect(Configuration configuration) throws ProcessorException {
        try {
            JSch jsch = new JSch();
            jsch.setKnownHosts(configuration.knownHosts().toString());
            Session session = jsch.getSession(
                    configuration.username(),
                    configuration.host(),
                    configuration.port());
            session.setPassword(configuration.password());
            session.setConfig("StrictHostKeyChecking", "yes");
            session.connect(10_000);
            ChannelSftp channel = (ChannelSftp) session.openChannel("sftp");
            channel.connect(10_000);
            return new SftpGateway(session, channel);
        } catch (JSchException exception) {
            throw new ProcessorException("SFTP_CONNECTION_ERROR", "Cannot establish verified SFTP connection", exception);
        }
    }

    @Override
    public void download(String remotePath, Path localPath) throws ProcessorException {
        try {
            channel.get(remotePath, localPath.toString());
        } catch (SftpException exception) {
            throw new ProcessorException("SFTP_DOWNLOAD_ERROR", "Cannot download required batch artifact", exception);
        }
    }

    @Override
    public void publish(
            String remoteDirectory,
            LinkedHashMap<String, Path> artifacts,
            String readinessManifest) throws ProcessorException {
        publishArtifacts(
                new ChannelPublicationOperations(channel),
                remoteDirectory,
                artifacts,
                readinessManifest);
    }

    public static void publishArtifacts(
            PublicationOperations operations,
            String remoteDirectory,
            LinkedHashMap<String, Path> artifacts,
            String readinessManifest) throws ProcessorException {
        if (!artifacts.containsKey(readinessManifest)) {
            throw new ProcessorException("INTERNAL_ERROR", "Publication is missing its readiness manifest");
        }
        boolean createdDirectory = false;
        try {
            if (operations.exists(remoteDirectory)) {
                throw new ProcessorException(
                        "SFTP_PUBLICATION_ERROR",
                        "Immutable sanitized batch directory already exists");
            }
            operations.makeDirectory(remoteDirectory);
            createdDirectory = true;
            operations.chmod(remoteDirectory, 0770);
            for (Map.Entry<String, Path> artifact : artifacts.entrySet()) {
                String temporaryName = remoteDirectory + "/" + artifact.getKey() + ".part";
                operations.upload(artifact.getValue(), temporaryName);
            }
            for (String name : artifacts.keySet()) {
                if (!name.equals(readinessManifest)) {
                    operations.rename(
                            remoteDirectory + "/" + name + ".part",
                            remoteDirectory + "/" + name);
                }
            }
            operations.rename(
                    remoteDirectory + "/" + readinessManifest + ".part",
                    remoteDirectory + "/" + readinessManifest);
        } catch (SftpException exception) {
            if (createdDirectory) {
                removePublicationDirectory(
                        operations,
                        remoteDirectory,
                        artifacts.keySet());
            }
            throw new ProcessorException("SFTP_PUBLICATION_ERROR", "Cannot atomically publish sanitized artifacts", exception);
        }
    }

    private static void removePublicationDirectory(
            PublicationOperations operations,
            String directory,
            Iterable<String> names) {
        for (String name : names) {
            try {
                operations.remove(directory + "/" + name + ".part");
            } catch (SftpException ignored) {
                // Continue removing any final artifacts.
            }
            try {
                operations.remove(directory + "/" + name);
            } catch (SftpException ignored) {
                // Continue so the batch directory can be removed when empty.
            }
        }
        try {
            operations.removeDirectory(directory);
        } catch (SftpException ignored) {
            // The absent readiness manifest keeps any unremovable residue invisible.
        }
    }

    public interface PublicationOperations {
        boolean exists(String path) throws SftpException;

        void makeDirectory(String path) throws SftpException;

        void chmod(String path, int permissions) throws SftpException;

        void upload(Path localPath, String remotePath) throws SftpException;

        void rename(String source, String target) throws SftpException;

        void remove(String path) throws SftpException;

        void removeDirectory(String path) throws SftpException;
    }

    private record ChannelPublicationOperations(
            ChannelSftp channel) implements PublicationOperations {
        @Override
        public boolean exists(String path) throws SftpException {
            try {
                channel.stat(path);
                return true;
            } catch (SftpException exception) {
                if (exception.id == ChannelSftp.SSH_FX_NO_SUCH_FILE) {
                    return false;
                }
                throw exception;
            }
        }

        @Override
        public void makeDirectory(String path) throws SftpException {
            channel.mkdir(path);
        }

        @Override
        public void chmod(String path, int permissions) throws SftpException {
            channel.chmod(permissions, path);
        }

        @Override
        public void upload(Path localPath, String remotePath) throws SftpException {
            channel.put(localPath.toString(), remotePath);
        }

        @Override
        public void rename(String source, String target) throws SftpException {
            channel.rename(source, target);
        }

        @Override
        public void remove(String path) throws SftpException {
            channel.rm(path);
        }

        @Override
        public void removeDirectory(String path) throws SftpException {
            channel.rmdir(path);
        }
    }

    @Override
    public void close() {
        if (channel.isConnected()) {
            channel.disconnect();
        }
        if (session.isConnected()) {
            session.disconnect();
        }
    }
}

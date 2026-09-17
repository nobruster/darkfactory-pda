package com.northwindpay.legacy.core;

import com.northwindpay.legacy.type01.Type01Processor;
import com.northwindpay.legacy.type02.Type02Processor;
import com.northwindpay.legacy.type03.Type03Processor;
import com.northwindpay.legacy.type04.Type04Processor;
import com.northwindpay.legacy.type05.Type05Processor;
import com.northwindpay.legacy.type06.Type06Processor;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Comparator;
import java.util.List;

/**
 * Command-line entrypoint for the typed legacy processor.
 *
 * <p>The launcher belongs to the shared application core because it registers
 * and dispatches every supported file type. Its arguments, JSON output, and
 * exit codes remain backward-compatible with the original Type 01 launcher.
 */
public final class ProcessorMain {
    private ProcessorMain() {
    }

    public static void main(String[] args) {
        String batchId = argument(args, "--batch-id");
        String expectedType = argument(args, "--type");
        ProcessorResult result;
        int exitCode;
        if (batchId == null) {
            result = ProcessorResult.rejected(
                    null,
                    expectedType,
                    new ProcessorException("USAGE_ERROR", "--batch-id is required"));
            exitCode = 2;
        } else {
            Path workingDirectory = null;
            try {
                Configuration configuration = Configuration.fromEnvironment(System.getenv());
                workingDirectory = Files.createTempDirectory("northwind-legacy-");
                try (SftpGateway sftp = SftpGateway.connect(configuration)) {
                    ProcessorDispatcher dispatcher =
                            new ProcessorDispatcher(List.of(
                                    new Type01Processor(),
                                    new Type02Processor(),
                                    new Type03Processor(),
                                    new Type04Processor(),
                                    new Type05Processor(),
                                    new Type06Processor()));
                    result = dispatcher.dispatch(
                            batchId,
                            expectedType,
                            configuration,
                            sftp,
                            workingDirectory);
                    exitCode = 0;
                }
            } catch (ProcessorException exception) {
                String selectedType = exception.typeNumber() == null
                        ? expectedType
                        : exception.typeNumber();
                result = ProcessorResult.rejected(
                        batchId,
                        selectedType,
                        exception);
                exitCode = 2;
            } catch (IOException exception) {
                result = ProcessorResult.type01Rejected(
                        batchId,
                        new ProcessorException(
                                "LOCAL_IO_ERROR",
                                "Cannot create private temporary workspace"));
                exitCode = 2;
            } finally {
                deleteRecursively(workingDirectory);
            }
        }

        exitCode = emit(result, exitCode);
        if (exitCode != 0) {
            System.exit(exitCode);
        }
    }

    private static int emit(ProcessorResult result, int exitCode) {
        try {
            System.out.println(StableJson.line(result.asMap()));
        } catch (ProcessorException exception) {
            System.out.println("{\"code\":\"INTERNAL_ERROR\",\"status\":\"rejected\"}");
            return 2;
        }
        return exitCode;
    }

    private static String argument(String[] args, String name) {
        for (int index = 0; index < args.length - 1; index++) {
            if (name.equals(args[index])) {
                return args[index + 1];
            }
        }
        return null;
    }

    private static void deleteRecursively(Path root) {
        if (root == null || !Files.exists(root)) {
            return;
        }
        try (var paths = Files.walk(root)) {
            paths.sorted(Comparator.reverseOrder()).forEach(path -> {
                try {
                    Files.deleteIfExists(path);
                } catch (IOException ignored) {
                    // Container termination removes the isolated temporary filesystem.
                }
            });
        } catch (IOException ignored) {
            // Container termination removes the isolated temporary filesystem.
        }
    }
}

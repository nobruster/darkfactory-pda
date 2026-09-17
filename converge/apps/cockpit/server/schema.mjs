import { readFile } from "node:fs/promises";
import path from "node:path";

const SNAPSHOT_SCHEMA_RELATIVE_PATH = path.join(
  "contracts",
  "ui",
  "v3",
  "workspace-snapshot.schema.json",
);

function isObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function sameJsonValue(left, right) {
  return JSON.stringify(left) === JSON.stringify(right);
}

function decodePointerSegment(segment) {
  return segment.replaceAll("~1", "/").replaceAll("~0", "~");
}

function resolveLocalReference(rootSchema, reference) {
  if (reference === "#") {
    return rootSchema;
  }
  if (!reference.startsWith("#/")) {
    throw new Error(`unsupported non-local schema reference: ${reference}`);
  }
  let current = rootSchema;
  for (const rawSegment of reference.slice(2).split("/")) {
    const segment = decodePointerSegment(rawSegment);
    if (!isObject(current) || !(segment in current)) {
      throw new Error(`unresolved schema reference: ${reference}`);
    }
    current = current[segment];
  }
  return current;
}

function matchesType(value, expected) {
  switch (expected) {
    case "array":
      return Array.isArray(value);
    case "integer":
      return Number.isInteger(value);
    case "null":
      return value === null;
    case "number":
      return typeof value === "number" && Number.isFinite(value);
    case "object":
      return isObject(value);
    case "string":
      return typeof value === "string";
    case "boolean":
      return typeof value === "boolean";
    default:
      return false;
  }
}

function isValidFormat(value, format) {
  if (format === "date-time") {
    return (
      typeof value === "string" &&
      /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(
        value,
      ) &&
      Number.isFinite(Date.parse(value))
    );
  }
  if (format === "uri") {
    try {
      new URL(value);
      return true;
    } catch {
      return false;
    }
  }
  return true;
}

function validateNode(value, schema, rootSchema, location, issues) {
  if (schema === true || schema === undefined) {
    return;
  }
  if (schema === false) {
    issues.push(`${location} is forbidden by the schema`);
    return;
  }
  if (!isObject(schema)) {
    issues.push(`${location} has an invalid schema definition`);
    return;
  }

  if (typeof schema.$ref === "string") {
    validateNode(
      value,
      resolveLocalReference(rootSchema, schema.$ref),
      rootSchema,
      location,
      issues,
    );
    return;
  }

  if (Array.isArray(schema.allOf)) {
    for (const candidate of schema.allOf) {
      validateNode(value, candidate, rootSchema, location, issues);
    }
  }
  if (Array.isArray(schema.anyOf)) {
    const matches = schema.anyOf.some((candidate) => {
      const candidateIssues = [];
      validateNode(value, candidate, rootSchema, location, candidateIssues);
      return candidateIssues.length === 0;
    });
    if (!matches) {
      issues.push(`${location} does not match any allowed schema`);
      return;
    }
  }
  if (Array.isArray(schema.oneOf)) {
    const matchCount = schema.oneOf.filter((candidate) => {
      const candidateIssues = [];
      validateNode(value, candidate, rootSchema, location, candidateIssues);
      return candidateIssues.length === 0;
    }).length;
    if (matchCount !== 1) {
      issues.push(`${location} must match exactly one allowed schema`);
      return;
    }
  }

  if ("const" in schema && !sameJsonValue(value, schema.const)) {
    issues.push(`${location} must equal ${JSON.stringify(schema.const)}`);
  }
  if (
    Array.isArray(schema.enum) &&
    !schema.enum.some((candidate) => sameJsonValue(value, candidate))
  ) {
    issues.push(`${location} is not an allowed value`);
  }

  if (schema.type !== undefined) {
    const expectedTypes = Array.isArray(schema.type)
      ? schema.type
      : [schema.type];
    if (!expectedTypes.some((expected) => matchesType(value, expected))) {
      issues.push(`${location} must be ${expectedTypes.join(" or ")}`);
      return;
    }
  }

  if (typeof value === "string") {
    if (Number.isInteger(schema.minLength) && value.length < schema.minLength) {
      issues.push(`${location} is shorter than ${schema.minLength}`);
    }
    if (Number.isInteger(schema.maxLength) && value.length > schema.maxLength) {
      issues.push(`${location} is longer than ${schema.maxLength}`);
    }
    if (typeof schema.pattern === "string") {
      let expression;
      try {
        expression = new RegExp(schema.pattern, "u");
      } catch {
        issues.push(`${location} uses an invalid schema pattern`);
        return;
      }
      if (!expression.test(value)) {
        issues.push(`${location} does not match the required pattern`);
      }
    }
    if (
      typeof schema.format === "string" &&
      !isValidFormat(value, schema.format)
    ) {
      issues.push(`${location} is not a valid ${schema.format}`);
    }
  }

  if (typeof value === "number") {
    if (typeof schema.minimum === "number" && value < schema.minimum) {
      issues.push(`${location} must be at least ${schema.minimum}`);
    }
    if (typeof schema.maximum === "number" && value > schema.maximum) {
      issues.push(`${location} must be at most ${schema.maximum}`);
    }
  }

  if (Array.isArray(value)) {
    if (Number.isInteger(schema.minItems) && value.length < schema.minItems) {
      issues.push(`${location} must contain at least ${schema.minItems} items`);
    }
    if (Number.isInteger(schema.maxItems) && value.length > schema.maxItems) {
      issues.push(`${location} must contain at most ${schema.maxItems} items`);
    }
    if (
      schema.uniqueItems === true &&
      new Set(value.map((item) => JSON.stringify(item))).size !== value.length
    ) {
      issues.push(`${location} must contain unique items`);
    }
    if (schema.items !== undefined) {
      value.forEach((item, index) =>
        validateNode(
          item,
          schema.items,
          rootSchema,
          `${location}[${index}]`,
          issues,
        ),
      );
    }
  }

  if (isObject(value)) {
    const properties = isObject(schema.properties) ? schema.properties : {};
    if (Array.isArray(schema.required)) {
      for (const name of schema.required) {
        if (!Object.hasOwn(value, name)) {
          issues.push(`${location}.${name} is required`);
        }
      }
    }
    for (const [name, propertyValue] of Object.entries(value)) {
      if (Object.hasOwn(properties, name)) {
        validateNode(
          propertyValue,
          properties[name],
          rootSchema,
          `${location}.${name}`,
          issues,
        );
      } else if (schema.additionalProperties === false) {
        issues.push(`${location}.${name} is not allowed`);
      } else if (isObject(schema.additionalProperties)) {
        validateNode(
          propertyValue,
          schema.additionalProperties,
          rootSchema,
          `${location}.${name}`,
          issues,
        );
      }
    }
  }
}

export function validateJsonSchema(value, schema) {
  const issues = [];
  validateNode(value, schema, schema, "$", issues);
  return issues;
}

function dependencyGraphIsAcyclic(legs) {
  const ids = new Set(legs.map((leg) => leg?.id));
  const indegree = new Map();
  const dependents = new Map();
  for (const id of ids) {
    indegree.set(id, 0);
    dependents.set(id, []);
  }
  for (const leg of legs) {
    if (!Array.isArray(leg?.dependsOn)) continue;
    for (const dependency of leg.dependsOn) {
      if (!ids.has(dependency) || !ids.has(leg.id)) continue;
      if (dependency === leg.id) return false;
      indegree.set(leg.id, (indegree.get(leg.id) ?? 0) + 1);
      dependents.get(dependency).push(leg.id);
    }
  }
  const frontier = [...ids].filter((id) => indegree.get(id) === 0);
  let visited = 0;
  while (frontier.length > 0) {
    const current = frontier.shift();
    visited += 1;
    for (const dependent of dependents.get(current) ?? []) {
      const next = indegree.get(dependent) - 1;
      indegree.set(dependent, next);
      if (next === 0) frontier.push(dependent);
    }
  }
  return visited === ids.size;
}

function entityReferenceIssues(snapshot) {
  if (
    !isObject(snapshot) ||
    !isObject(snapshot.project) ||
    typeof snapshot.project.name !== "string" ||
    !isObject(snapshot.method) ||
    !isObject(snapshot.decomposition) ||
    !isObject(snapshot.work) ||
    !isObject(snapshot.execution) ||
    !isObject(snapshot.receipts) ||
    !isObject(snapshot.health) ||
    !Array.isArray(snapshot.method.passes) ||
    !Array.isArray(snapshot.decomposition.swimlanes) ||
    !Array.isArray(snapshot.decomposition.legs) ||
    !Array.isArray(snapshot.decomposition.edges) ||
    !Array.isArray(snapshot.work.tasks) ||
    !Array.isArray(snapshot.execution.runs) ||
    !Array.isArray(snapshot.receipts.items) ||
    !Array.isArray(snapshot.health.checks) ||
    !Array.isArray(snapshot.signals) ||
    !Array.isArray(snapshot.issues) ||
    !Array.isArray(snapshot.artifacts)
  ) {
    return [];
  }

  const collections = {
    pass: snapshot.method.passes,
    swimlane: snapshot.decomposition.swimlanes,
    leg: snapshot.decomposition.legs,
    task: snapshot.work.tasks,
    run: snapshot.execution.runs,
    receipt: snapshot.receipts.items,
    health: snapshot.health.checks,
    signal: snapshot.signals,
    issue: snapshot.issues,
    artifact: snapshot.artifacts,
  };
  const known = {
    project: new Set([snapshot.project.name]),
  };
  const issues = [];

  for (const [kind, records] of Object.entries(collections)) {
    const ids = records.map((record) => record?.id);
    if (ids.some((id) => typeof id !== "string")) {
      return [];
    }
    if (new Set(ids).size !== ids.length) {
      issues.push(`$.${kind} entities must have unique ids`);
    }
    known[kind] = new Set(ids);
  }

  const containers = [
    ["signals", snapshot.signals],
    ["issues", snapshot.issues],
    ["artifacts", snapshot.artifacts],
  ];
  for (const [collectionName, records] of containers) {
    records.forEach((record, index) => {
      if (!isObject(record?.entity)) {
        return;
      }
      const { kind, id } = record.entity;
      if (
        typeof kind === "string" &&
        typeof id === "string" &&
        known[kind] instanceof Set &&
        !known[kind].has(id)
      ) {
        issues.push(
          `$.${collectionName}[${index}].entity references unknown ${kind} ${JSON.stringify(id)}`,
        );
      }
    });
  }

  const knownArtifactIds = known.artifact;
  const inspectArtifactReferences = (value, location) => {
    if (Array.isArray(value)) {
      value.forEach((item, index) =>
        inspectArtifactReferences(item, `${location}[${index}]`),
      );
      return;
    }
    if (!isObject(value)) return;
    for (const [name, child] of Object.entries(value)) {
      const childLocation = `${location}.${name}`;
      if (name === "artifactIds" && Array.isArray(child)) {
        child.forEach((artifactId, index) => {
          if (
            typeof artifactId === "string" &&
            !knownArtifactIds.has(artifactId)
          ) {
            issues.push(
              `${childLocation}[${index}] references unknown artifact ${JSON.stringify(artifactId)}`,
            );
          }
        });
      } else {
        inspectArtifactReferences(child, childLocation);
      }
    }
  };
  inspectArtifactReferences(snapshot, "$");

  const lanesById = new Map(
    snapshot.decomposition.swimlanes.map((lane) => [lane.id, lane]),
  );
  const legsById = new Map(
    snapshot.decomposition.legs.map((leg) => [leg.id, leg]),
  );
  snapshot.decomposition.swimlanes.forEach((lane, laneIndex) => {
    if (!Array.isArray(lane.legIds)) return;
    lane.legIds.forEach((legId, legIndex) => {
      const leg = legsById.get(legId);
      if (!leg) {
        issues.push(
          `$.decomposition.swimlanes[${laneIndex}].legIds[${legIndex}] references unknown leg ${JSON.stringify(legId)}`,
        );
      } else if (leg.swimlaneId !== lane.id) {
        issues.push(
          `$.decomposition.swimlanes[${laneIndex}].legIds[${legIndex}] belongs to a different swimlane`,
        );
      }
    });
  });
  snapshot.decomposition.legs.forEach((leg, legIndex) => {
    const lane = lanesById.get(leg.swimlaneId);
    if (!lane) {
      issues.push(
        `$.decomposition.legs[${legIndex}].swimlaneId references unknown swimlane ${JSON.stringify(leg.swimlaneId)}`,
      );
    } else if (Array.isArray(lane.legIds) && !lane.legIds.includes(leg.id)) {
      issues.push(
        `$.decomposition.legs[${legIndex}] is absent from its swimlane legIds`,
      );
    }
    if (!Array.isArray(leg.dependsOn)) return;
    leg.dependsOn.forEach((dependency, dependencyIndex) => {
      if (!legsById.has(dependency)) {
        issues.push(
          `$.decomposition.legs[${legIndex}].dependsOn[${dependencyIndex}] references unknown leg ${JSON.stringify(dependency)}`,
        );
      }
    });
  });
  if (!dependencyGraphIsAcyclic(snapshot.decomposition.legs)) {
    issues.push("$.decomposition leg dependencies must form an acyclic graph");
  }
  const edgeIds = snapshot.decomposition.edges.map((edge) => edge?.id);
  if (new Set(edgeIds).size !== edgeIds.length) {
    issues.push("$.decomposition.edges must have unique ids");
  }
  const expectedDependencyPairs = new Set(
    snapshot.decomposition.legs.flatMap((leg) =>
      Array.isArray(leg.dependsOn)
        ? leg.dependsOn.map((dependency) => `${dependency}\u0000${leg.id}`)
        : [],
    ),
  );
  const observedDependencyPairs = new Set();
  snapshot.decomposition.edges.forEach((edge, edgeIndex) => {
    const source = legsById.get(edge?.source);
    const target = legsById.get(edge?.target);
    if (!source || !target) {
      issues.push(
        `$.decomposition.edges[${edgeIndex}] references an unknown leg`,
      );
    } else if (!Array.isArray(target.dependsOn) || !target.dependsOn.includes(source.id)) {
      issues.push(
        `$.decomposition.edges[${edgeIndex}] is not declared by its target dependsOn`,
      );
    }
    const pair = `${edge?.source}\u0000${edge?.target}`;
    if (observedDependencyPairs.has(pair)) {
      issues.push(
        `$.decomposition.edges[${edgeIndex}] duplicates a dependency edge`,
      );
    }
    observedDependencyPairs.add(pair);
  });
  if (
    expectedDependencyPairs.size !== observedDependencyPairs.size ||
    [...expectedDependencyPairs].some(
      (pair) => !observedDependencyPairs.has(pair),
    )
  ) {
    issues.push(
      "$.decomposition.edges must exactly represent every leg dependsOn relationship",
    );
  }
  if (
    snapshot.decomposition.availability !== "available" &&
    (snapshot.decomposition.swimlanes.length > 0 ||
      snapshot.decomposition.legs.length > 0 ||
      snapshot.decomposition.edges.length > 0)
  ) {
    issues.push(
      "$.decomposition must not retain partial records when unavailable or empty",
    );
  }
  return issues;
}

export function snapshotSchemaPath(config) {
  if (!config?.cvgHome) {
    throw new Error("snapshot schema resolution requires CVG_HOME");
  }
  return path.join(config.cvgHome, SNAPSHOT_SCHEMA_RELATIVE_PATH);
}

export async function createWorkspaceSnapshotValidator({
  config,
  schemaPath = snapshotSchemaPath(config),
} = {}) {
  let schema;
  try {
    schema = JSON.parse(await readFile(schemaPath, "utf8"));
  } catch (error) {
    const wrapped = new Error(
      `WorkspaceSnapshot 3.0 schema is unavailable: ${schemaPath}`,
      { cause: error },
    );
    wrapped.code = "SNAPSHOT_SCHEMA_UNAVAILABLE";
    throw wrapped;
  }

  return (snapshot) => {
    const issues = validateJsonSchema(snapshot, schema);
    if (
      !isObject(snapshot) ||
      snapshot.schemaVersion !== "3.0" ||
      typeof snapshot.snapshotId !== "string" ||
      snapshot.snapshotId.length === 0 ||
      !Array.isArray(snapshot.artifacts)
    ) {
      issues.push(
        "$ must be a WorkspaceSnapshot 3.0 with snapshotId and artifacts",
      );
    }
    if (issues.length === 0) {
      issues.push(...entityReferenceIssues(snapshot));
    }
    if (issues.length > 0) {
      const error = new Error(
        `WorkspaceSnapshot 3.0 failed validation: ${issues
          .slice(0, 8)
          .join("; ")}`,
      );
      error.code = "SNAPSHOT_SCHEMA_INVALID";
      error.issues = issues;
      throw error;
    }
    return snapshot;
  };
}

export { SNAPSHOT_SCHEMA_RELATIVE_PATH };

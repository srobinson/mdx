import { describe, expect, test } from "vitest";
import { Vector3 } from "three";
import {
  applySceneOperation,
  classifyAuthoredRenderImpact,
  createCubeSelectionSet,
  createDetachedWorkbench,
  createSceneGridLayout,
  defaultScene,
  deriveInverseBody,
  getWorkingScene,
  materializeSceneOperations,
  updateWorkingScene,
} from "../src/domain";
import { rotateAroundAxisInto } from "../src/shared/axisRotation";
import { decodeCompactPose, encodeCompactPose } from "../src/persistence/recordCodecs/compactPose";
import { createRotationBasis } from "../src/domain/worldGeometry";
import { createFilledGridScene } from "./sceneTestHelpers";

describe("turn selection", () => {
  const before = createFilledGridScene(defaultScene, { x: 2, y: 1, z: 1 });
  const operation = {
    amount: "quarter" as const,
    axis: "z" as const,
    direction: 1 as const,
    kind: "turn-selection" as const,
    scope: {
      cubeIds: before.cells.map(({ id }) => id),
      kind: "ids" as const,
    },
  };

  test("rotates selected cubes jointly about their shared pivot", () => {
    const previousLayout = createSceneGridLayout(before.grid, before.cells);
    const after = applySceneOperation(before, operation);
    const nextLayout = createSceneGridLayout(after.grid, after.cells);
    const [firstId, secondId] = operation.scope.cubeIds;

    expect(nextLayout[firstId].renderPosition[0]).toBeCloseTo(0, 12);
    expect(nextLayout[firstId].renderPosition[1]).toBeCloseTo(
      previousLayout[firstId].renderPosition[0],
      12,
    );
    expect(nextLayout[secondId].renderPosition[0]).toBeCloseTo(0, 12);
    expect(nextLayout[secondId].renderPosition[1]).toBeCloseTo(
      previousLayout[secondId].renderPosition[0],
      12,
    );
    expect(distance(nextLayout[firstId].renderPosition, nextLayout[secondId].renderPosition)).toBe(
      distance(previousLayout[firstId].renderPosition, previousLayout[secondId].renderPosition),
    );
  });

  test("keeps logical coordinates fixed while authoring offset and rotation", () => {
    const after = applySceneOperation(before, operation);

    expect(after.cells.map(({ placement }) => placement.coord)).toEqual(
      before.cells.map(({ placement }) => placement.coord),
    );
    for (const cell of after.cells) {
      expect(cell.placement.rotation[0]).toBeCloseTo(0, 12);
      expect(cell.placement.rotation[1]).toBeCloseTo(0, 12);
      expect(cell.placement.rotation[2]).toBeCloseTo(Math.PI / 2, 12);
    }
  });

  test("maps positive Z from render right toward render up", () => {
    const previousLayout = createSceneGridLayout(before.grid, before.cells);
    const after = applySceneOperation(before, operation);
    const nextLayout = createSceneGridLayout(after.grid, after.cells);
    const cubeId = before.cells[1].id;
    const radius = previousLayout[cubeId].renderPosition[0];
    const rendered = new Vector3(...nextLayout[cubeId].renderPosition).divideScalar(radius);
    const expected = new Vector3(1, 0, 0).applyAxisAngle(new Vector3(0, 0, 1), Math.PI / 2);

    for (const axis of ["x", "y", "z"] as const) {
      expect(rendered[axis]).toBeCloseTo(expected[axis], 12);
    }
    expect(rendered.y).toBeGreaterThan(0);
  });

  test("composes the turn with an existing orientation as a rigid body", () => {
    const rotation: [number, number, number] = [0.3, -0.4, 0.2];
    const oriented = {
      ...before,
      cells: [
        {
          ...before.cells[0],
          placement: { ...before.cells[0].placement, rotation },
        },
      ],
    };
    const after = applySceneOperation(oriented, {
      ...operation,
      scope: { cubeId: oriented.cells[0].id, kind: "single" },
    });
    const expected = createRotationBasis(rotation).map((basisAxis) =>
      rotateAroundAxisInto([0, 0, 0], basisAxis, [0, 0, 1], Math.PI / 2),
    );
    const actual = createRotationBasis(after.cells[0].placement.rotation);

    for (const [axisIndex, axis] of actual.entries()) {
      for (const [valueIndex, value] of axis.entries()) {
        expect(value).toBeCloseTo(expected[axisIndex][valueIndex], 12);
      }
    }
  });

  test("preserves an authored unwrapped rotation while composing", () => {
    const unwrapped = {
      ...before,
      cells: [
        {
          ...before.cells[0],
          placement: {
            ...before.cells[0].placement,
            rotation: [0, 0, Math.PI * 2] as [number, number, number],
          },
        },
      ],
    };

    const after = applySceneOperation(unwrapped, {
      ...operation,
      scope: { cubeId: unwrapped.cells[0].id, kind: "single" },
    });

    expect(after.cells[0].placement.rotation[2]).toBeCloseTo((Math.PI * 5) / 2, 12);
  });

  test("materializes contextual selection and reports bounded cell transform impact", () => {
    const selectionSet = createCubeSelectionSet(
      before.cells.map(({ id }) => ({ cubeId: id, kind: "cube" })),
    );
    const [materialized] = materializeSceneOperations(
      before,
      { ...operation, scope: { kind: "selection-set" } },
      { selectionSet },
    );
    const after = applySceneOperation(before, materialized);
    const impact = classifyAuthoredRenderImpact(
      { family: "scene", operations: [materialized] },
      before,
      after,
    );

    expect(materialized).toMatchObject({
      scope: {
        cubeIds: before.cells.map(({ id }) => id),
        kind: "ids",
      },
    });
    expect(impact.kind).toBe("cells");
    if (impact.kind !== "cells") throw new Error("cell impact");
    expect([...impact.cells.keys()]).toEqual(before.cells.map(({ id }) => id));
    for (const cellImpact of impact.cells.values()) {
      expect(cellImpact).toMatchObject({ occupancy: false, transform: true });
    }
  });

  test("restores the original pose exactly through the authored inverse", () => {
    const after = applySceneOperation(before, operation);
    const workbenchBefore = createDetachedWorkbench(before);
    const workbenchAfter = updateWorkingScene(workbenchBefore, after);
    const inverse = deriveInverseBody(
      workbenchBefore,
      { family: "scene", operations: [operation] },
      workbenchAfter,
    );

    expect(inverse?.family).toBe("scene");
    if (!inverse || inverse.family !== "scene") throw new Error("scene inverse");
    const restored = inverse.operations.reduce(
      (scene, inverseOperation) => applySceneOperation(scene, inverseOperation),
      after,
    );
    expect(restored).toEqual(getWorkingScene(workbenchBefore));
  });

  test("persists the authored pose through compact storage", () => {
    const after = applySceneOperation(before, operation);

    const decoded = decodeCompactPose(encodeCompactPose(after));

    expect(decoded.ok).toBe(true);
    if (!decoded.ok) throw new Error(decoded.error);
    expect(decoded.value.cells).toEqual(after.cells);
  });
});

test("shared axis rotation preserves the previous camera maths bit for bit", () => {
  const destination: [number, number, number] = [0, 0, 0];

  expect(rotateAroundAxisInto(destination, [2, -3, 5], [0, 1, 0], 0.37)).toEqual([
    3.672731851036879, -3, 3.9384058641002486,
  ]);
});

function distance(
  left: readonly [number, number, number],
  right: readonly [number, number, number],
): number {
  return Math.hypot(left[0] - right[0], left[1] - right[1], left[2] - right[2]);
}

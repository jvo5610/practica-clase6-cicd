import test from "node:test";
import assert from "node:assert/strict";

import { calculateProgress, getStatusMessage, stages } from "../src/app.js";

test("el pipeline conserva las cinco etapas explicadas en clase", () => {
  assert.deepEqual(
    stages.map((stage) => stage.title),
    ["Código", "Validación", "Construcción", "Paquete", "Despliegue"]
  );
});

test("calcula el porcentaje de avance", () => {
  assert.equal(calculateProgress(0, 5), 0);
  assert.equal(calculateProgress(2, 5), 40);
  assert.equal(calculateProgress(5, 5), 100);
});

test("limita valores fuera del rango del pipeline", () => {
  assert.equal(calculateProgress(-1, 5), 0);
  assert.equal(calculateProgress(9, 5), 100);
});

test("rechaza cantidades inválidas", () => {
  assert.throws(() => calculateProgress(1, 0), TypeError);
  assert.throws(() => calculateProgress(1.5, 5), TypeError);
});

test("informa cuándo la entrega llegó a producción", () => {
  assert.match(getStatusMessage(5, 5), /producción/);
});


/**
 * Schema validation helper (T028)
 * Wraps an Ajv instance; allows registration of JSON Schemas tied to logical names.
 */
// Ajv integration (typed loosely to avoid build-time friction until stricter usage needed)
import Ajv from 'ajv';
import addFormats from 'ajv-formats';
import type { ValidateFunction, ErrorObject } from 'ajv';

export interface SchemaValidationResult<T = unknown> {
  valid: boolean;
  errors?: ErrorObject[];
  data?: T;
}

class SchemaRegistry {
  // Using any to sidestep constructor signature/type resolution issues under NodeNext until stricter enforcement needed.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private ajv: any;
  private validators: Map<string, ValidateFunction> = new Map();

  constructor() {
  this.ajv = new (Ajv as any)({ allErrors: true, strict: true });
  (addFormats as any)(this.ajv);
  }

  register(name: string, schema: object) {
  const validate: ValidateFunction = this.ajv.compile(schema);
  this.validators.set(name, validate);
  }

  validate<T = unknown>(name: string, data: unknown): SchemaValidationResult<T> {
    const fn = this.validators.get(name);
    if (!fn) throw new Error(`Schema '${name}' not registered`);
    const valid = fn(data) as boolean;
    if (!valid) {
      return { valid: false, errors: fn.errors || undefined };
    }
    return { valid: true, data: data as T };
  }
}

export const schemaRegistry = new SchemaRegistry();

export function registerSchema(name: string, schema: object) {
  schemaRegistry.register(name, schema);
}

export function validateSchema<T>(name: string, data: unknown): SchemaValidationResult<T> {
  return schemaRegistry.validate<T>(name, data);
}

import type {
  Brand,
  EmitterId,
  LayerId,
  ParameterKey,
  ParameterValue,
  Patch,
  Seed,
  VoiceId,
  VoiceRequest,
  ValidationIssue
} from "/Users/alphab/Dev/LLM/DEV/helioy/audioface-next/packages/contract/src/index.ts";
import type { ParameterDefinition } from "/Users/alphab/Dev/LLM/DEV/helioy/audioface-next/packages/patch/src/registry/definition.ts";

// Proposed names. Existing domain types above remain authoritative.
type SoundInstanceId = Brand<string, "SoundInstanceId">;
type PluginId = Brand<string, "PluginId">;
type PluginInstanceId = Brand<string, "PluginInstanceId">;
type PortId = Brand<string, "PortId">;
type PackEventRef = { readonly packId: string; readonly eventId: string };
type BoundRevision = {
  readonly binding: PackEventRef;
  readonly revision: number;
  readonly patch: Patch;
};

type CloneValue =
  | null | boolean | number | string
  | readonly CloneValue[]
  | { readonly [key: string]: CloneValue };

type PreparedPluginPlan = {
  readonly pluginId: PluginId;
  readonly version: string;
  readonly instanceId: PluginInstanceId;
  readonly configuration: CloneValue;
  readonly seed: Seed | null;
};

type PreparedSoundPlan = {
  readonly binding: PackEventRef;
  readonly revision: number;
  readonly sampleRate: number;
  readonly layers: readonly {
    readonly id: LayerId;
    readonly plugins: readonly PreparedPluginPlan[];
  }[];
  readonly soundPlugins: readonly PreparedPluginPlan[];
};

type SoundHandleState =
  | { readonly kind: "preparing" }
  | { readonly kind: "open"; readonly activity: "idle" | "active" }
  | { readonly kind: "closing" }
  | { readonly kind: "retired" }
  | { readonly kind: "refused"; readonly issues: readonly ValidationIssue<string>[] }
  | { readonly kind: "invalidated"; readonly reason: "device-rebuilt" };

type SoundHandle = {
  readonly id: SoundInstanceId;
  readonly trigger: (request: Pick<VoiceRequest, "take" | "listener">) => VoiceId;
  readonly release: (voice: VoiceId) => boolean;
  readonly dispose: () => void;
  readonly state: () => SoundHandleState;
};

type SoundCreation = {
  readonly event: string;
  readonly emitter: EmitterId;
};

type EffectiveValue =
  | { readonly kind: "unresolved" }
  | { readonly kind: "preview"; readonly take: number; readonly value: ParameterValue }
  | {
      readonly kind: "runtime";
      readonly soundId: SoundInstanceId;
      readonly frame: number;
      readonly value: ParameterValue;
    };

type WritableControl = {
  readonly kind: "authored";
  readonly key: ParameterKey;
  readonly authored: ParameterValue;
  readonly characterOverride: ParameterValue | null;
  readonly lifetime: ParameterDefinition["lifetime"];
  readonly effective: EffectiveValue;
};

type DerivedControl = {
  readonly kind: "derived";
  readonly key: ParameterKey;
  readonly effective: EffectiveValue;
};

type AudioPort = {
  readonly id: PortId;
  readonly channels: readonly Float32Array[];
};

type ControlPort =
  | { readonly id: PortId; readonly rate: "control"; value: number }
  | { readonly id: PortId; readonly rate: "audio"; readonly values: Float32Array };

type RenderBlock = {
  readonly startFrame: number;
  readonly frameCount: number;
  readonly ageFrames: number;
  readonly audioIn: readonly AudioPort[];
  readonly audioOut: readonly AudioPort[];
  readonly controlIn: readonly ControlPort[];
  readonly controlOut: readonly ControlPort[];
  readonly events: {
    readonly count: number;
    readonly slots: readonly {
      readonly portId: PortId;
      readonly offset: number;
      readonly payload: CloneValue;
    }[];
  };
};

type Capability<Operation> =
  | { readonly kind: "unsupported" }
  | { readonly kind: "supported"; readonly operation: Operation };

// Engine-private instance. It cannot be sent as the prepared data plan.
type PluginInstance = {
  readonly process: (block: RenderBlock) => void;
  readonly reset: Capability<() => void>;
  readonly state: Capability<{
    readonly schemaVersion: number;
    readonly save: () => Uint8Array;
    readonly restore: (state: Uint8Array) => void;
  }>;
  readonly latencyFrames: () => number;
  readonly tailFrames: () => number;
};

type Preparation<Value> =
  | { readonly ok: true; readonly value: Value }
  | { readonly ok: false; readonly issues: readonly ValidationIssue<string>[] };

type ConfigurationRequest = {
  readonly parameters: Readonly<Record<ParameterKey, ParameterValue>>;
  readonly sampleRate: number;
};

type PreparedConfiguration = {
  readonly data: CloneValue;
  readonly maximumDspBytes: number;
};

// Partial definition view. Issue 4 supplies the remaining declared fields.
type PluginDefinition = {
  readonly id: PluginId;
  readonly version: string;
  readonly scope: "voice" | "sound";
  readonly parameters: readonly ParameterDefinition[];
};

// prepare is pure; create is audio-realm local and may fail without pool mutation.
// The receiving boundary validates serialized configuration against its module.
type PluginModule = {
  readonly definition: PluginDefinition;
  readonly prepare: (request: ConfigurationRequest) => Preparation<PreparedConfiguration>;
  readonly create: (context: {
    readonly configuration: PreparedConfiguration;
    readonly seed: Seed | null;
  }) => Preparation<PluginInstance>;
};

// Required boot policy. The boundary validates finite positive safe integers.
// No unbounded fallback or hidden default is permitted.
type HostBudget = {
  readonly maximumSoundHandles: number;
  readonly maximumPreparedStarts: number;
  readonly maximumDspBytes: number;
};

declare const plan: PreparedSoundPlan;
declare const instance: PluginInstance;
declare const voiceId: VoiceId;
declare const derived: DerivedControl;
declare function setControl(control: WritableControl, value: ParameterValue): void;

const transferablePlan: CloneValue = plan;
// @ts-expect-error Runtime functions are not cloneable preparation data.
const nonTransferableInstance: CloneValue = instance;
// @ts-expect-error A Voice is not a Sound identity.
const wrongIdentity: SoundInstanceId = voiceId;
// @ts-expect-error Derived values cannot be submitted through the authored setter.
setControl(derived, 100);

void transferablePlan;
void nonTransferableInstance;
void wrongIdentity;

export type {
  BoundRevision,
  PreparedSoundPlan,
  SoundHandle,
  SoundCreation,
  EffectiveValue,
  WritableControl,
  DerivedControl,
  RenderBlock,
  PluginInstance,
  PluginModule,
  PreparedConfiguration,
  HostBudget
};

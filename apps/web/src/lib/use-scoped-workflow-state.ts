import {
  useCallback,
  useState,
  type Dispatch,
  type SetStateAction,
} from "react";

/** A scope change invalidates both rendered data and all previous async setters. */
export function useScopedWorkflowState<T>(
  scope: string,
  initial: T | (() => T),
): readonly [T, Dispatch<SetStateAction<T>>] {
  const create = () => ({
    scope,
    generation: {},
    value: typeof initial === "function" ? (initial as () => T)() : initial,
  });
  const [stored, setStored] = useState(create);
  let current = stored;
  if (stored.scope !== scope) {
    current = create();
    setStored(current);
  }
  const generation = current.generation;
  const setValue = useCallback<Dispatch<SetStateAction<T>>>(
    (update) => {
      setStored((latest) =>
        latest.generation !== generation
          ? latest
          : {
              ...latest,
              value:
                typeof update === "function"
                  ? (update as (value: T) => T)(latest.value)
                  : update,
            },
      );
    },
    [generation],
  );
  return [current.value, setValue];
}

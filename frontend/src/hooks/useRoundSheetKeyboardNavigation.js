import { useCallback, useEffect, useRef } from "react";
import { findFocusStepIndex, focusStepId } from "@/lib/roundSheetFocusOrder";

function isTextInput(element) {
  if (!element) return false;
  const tag = element.tagName?.toLowerCase();
  return tag === "input" || tag === "textarea" || tag === "select";
}

function caretAtStart(element) {
  if (!isTextInput(element)) return true;
  if (element.type === "number") return true;
  return (element.selectionStart ?? 0) === 0;
}

function caretAtEnd(element) {
  if (!isTextInput(element)) return true;
  if (element.type === "number") return true;
  const length = element.value?.length ?? 0;
  return (element.selectionStart ?? length) >= length;
}

function focusElement(element) {
  if (!element || element.disabled) return false;
  element.focus({ preventScroll: false });
  element.scrollIntoView({ block: "nearest", inline: "nearest", behavior: "smooth" });
  return true;
}

/**
 * Registry-based keyboard navigation for round sheet focus order.
 * @param {Array<{ type: string, key?: string }>} focusChain
 */
export function useRoundSheetKeyboardNavigation(focusChain) {
  const registryRef = useRef(new Map());

  const register = useCallback((stepId, element) => {
    if (element) {
      registryRef.current.set(stepId, element);
    } else {
      registryRef.current.delete(stepId);
    }
  }, []);

  const getRef = useCallback(
    (stepId) => (element) => register(stepId, element),
    [register]
  );

  const focusByStepId = useCallback(
    (stepId) => {
      const element = registryRef.current.get(stepId);
      return focusElement(element);
    },
    []
  );

  const focusByIndex = useCallback(
    (index) => {
      if (index < 0 || index >= focusChain.length) return false;
      return focusByStepId(focusStepId(focusChain[index]));
    },
    [focusByStepId, focusChain]
  );

  const focusRelative = useCallback(
    (currentStepId, delta) => {
      const currentIndex = findFocusStepIndex(focusChain, currentStepId);
      if (currentIndex === -1) return false;

      let nextIndex = currentIndex + delta;
      while (nextIndex >= 0 && nextIndex < focusChain.length) {
        if (focusByIndex(nextIndex)) return true;
        nextIndex += delta > 0 ? 1 : -1;
      }
      return false;
    },
    [focusByIndex, focusChain]
  );

  const focusFirst = useCallback(() => {
    return focusByIndex(0);
  }, [focusByIndex]);

  const handleNavigationKeyDown = useCallback(
    (event, currentStepId) => {
      const { key, shiftKey, currentTarget } = event;

      if (key === "Enter") {
        event.preventDefault();
        if (shiftKey) {
          focusRelative(currentStepId, -1);
        } else {
          focusRelative(currentStepId, 1);
        }
        return true;
      }

      if (key === "ArrowDown") {
        event.preventDefault();
        focusRelative(currentStepId, 1);
        return true;
      }

      if (key === "ArrowUp") {
        event.preventDefault();
        focusRelative(currentStepId, -1);
        return true;
      }

      if (key === "ArrowRight") {
        if (caretAtEnd(currentTarget)) {
          event.preventDefault();
          focusRelative(currentStepId, 1);
          return true;
        }
        return false;
      }

      if (key === "ArrowLeft") {
        if (caretAtStart(currentTarget)) {
          event.preventDefault();
          focusRelative(currentStepId, -1);
          return true;
        }
        return false;
      }

      return false;
    },
    [focusRelative]
  );

  useEffect(() => {
    registryRef.current.clear();
  }, [focusChain]);

  return {
    getRef,
    focusByStepId,
    focusFirst,
    focusRelative,
    handleNavigationKeyDown,
  };
}

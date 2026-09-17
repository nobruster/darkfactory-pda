# State Machines for Conversations

> **Purpose**: Finite state machines (FSM) for deterministic conversational flow control with LLM-powered transitions
> **Confidence**: 0.95
> **MCP Validated**: 2026-02-17

## Overview

State machines bring deterministic control to LLM-powered conversations. Each conversation exists in exactly one state at a time, with defined transitions triggered by user input or LLM decisions. This hybrid approach combines the reliability of rule-based systems with the flexibility of LLMs: the FSM enforces structure, while the LLM handles natural language understanding within each state.

## The Pattern

```python
from dataclasses import dataclass, field
from typing import Callable, Optional
from enum import Enum, auto

class ConversationState(Enum):
    GREETING = auto()
    INTENT_DETECTION = auto()
    INFORMATION_GATHERING = auto()
    PROCESSING = auto()
    CONFIRMATION = auto()
    ESCALATION = auto()
    FAREWELL = auto()

@dataclass
class Transition:
    from_state: ConversationState
    to_state: ConversationState
    condition: str  # evaluated by LLM or rule
    action: Optional[Callable] = None

@dataclass
class StateConfig:
    state: ConversationState
    system_prompt: str
    required_slots: list[str] = field(default_factory=list)
    max_turns: int = 5
    fallback_state: Optional[ConversationState] = None

class ConversationFSM:
    def __init__(self, states: dict[ConversationState, StateConfig],
                 transitions: list[Transition]):
        self.states = states
        self.transitions = transitions
        self.current_state = ConversationState.GREETING
        self.context: dict = {}
        self.turn_count: int = 0

    def process(self, user_input: str) -> tuple[str, ConversationState]:
        """Process user input and return (response, new_state)."""
        config = self.states[self.current_state]
        self.turn_count += 1
        if self.turn_count > config.max_turns:
            self.current_state = config.fallback_state or ConversationState.ESCALATION
            return "Let me connect you with a specialist.", self.current_state
        response = self._generate_in_state(user_input, config)
        next_state = self._evaluate_transitions(user_input, response)
        if next_state != self.current_state:
            self.current_state = next_state
            self.turn_count = 0
        return response, self.current_state
```

## Quick Reference

| State Pattern | Description | Example |
|---------------|-------------|---------|
| Linear | Fixed sequence of states | Onboarding wizard |
| Branching | Multiple paths from one state | Intent routing |
| Looping | Return to previous state | Slot filling |
| Parallel | Multiple active substates | Multi-topic chat |
| Hierarchical | Nested state machines | Complex workflows |

## Design Principles

```text
1. Each state has ONE clear purpose (single responsibility)
2. Transitions are explicit and auditable (no hidden jumps)
3. Every state has a fallback/timeout (no dead ends)
4. Slot filling happens within states (not across)
5. LLM decides WITHIN states; rules decide BETWEEN states
```

## Common Mistakes

### Wrong

```python
# No state boundaries -- LLM controls entire flow
response = llm.chat("You are a support bot. Handle everything.")
# Result: unpredictable flow, no auditability, no escalation
```

### Correct

```python
states = {
    ConversationState.INTENT_DETECTION: StateConfig(
        state=ConversationState.INTENT_DETECTION,
        system_prompt="Classify user intent into: billing, technical, general.",
        max_turns=2,
        fallback_state=ConversationState.ESCALATION,
    ),
    ConversationState.INFORMATION_GATHERING: StateConfig(
        state=ConversationState.INFORMATION_GATHERING,
        system_prompt="Collect required information. Ask one question at a time.",
        required_slots=["account_id", "issue_description"],
        max_turns=5,
        fallback_state=ConversationState.ESCALATION,
    ),
}
```

## Integration with LangGraph

```python
from langgraph.graph import StateGraph, END

workflow = StateGraph(ConversationContext)
workflow.add_node("greet", greet_node)
workflow.add_node("classify", classify_intent_node)
workflow.add_node("gather_info", gather_info_node)
workflow.add_node("resolve", resolve_node)

workflow.add_edge("greet", "classify")
workflow.add_conditional_edges("classify", route_by_intent, {
    "billing": "gather_info",
    "technical": "gather_info",
    "general": "resolve",
})
workflow.add_edge("gather_info", "resolve")
workflow.add_edge("resolve", END)
```

## Related

- [Multi-Agent Systems](../concepts/multi-agent-systems.md)
- [Chatbot Architecture Pattern](../patterns/chatbot-architecture.md)
- [Guardrails](../concepts/guardrails.md)

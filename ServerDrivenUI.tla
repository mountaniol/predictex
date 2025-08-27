----------------------- MODULE ServerDrivenUI -----------------------

EXTENDS Integers, Sequences, TLC, FiniteSets

CONSTANTS 
    Commands,        \* Set of available SSE commands
    Events,          \* Set of user events
    ComponentStates, \* Set of UI component states
    MaxQueueSize,    \* Maximum command queue size
    MaxRetries       \* Maximum retry attempts

VARIABLES
    \* Command Processing System
    commandQueue,        \* Sequence of pending commands
    commandProcessor,    \* State of command processor
    
    \* Event Dispatching System  
    eventQueue,          \* Pending user events
    eventDispatcher,     \* State of event dispatcher
    networkStatus,       \* Connection status
    retryCount,         \* Current retry count
    
    \* State Synchronization
    frontendState,      \* Current frontend state
    backendState,       \* Authoritative backend state
    syncStatus,         \* Synchronization status
    
    \* UI Rendering System
    componentStates,    \* States of all UI components
    renderQueue,        \* Pending render operations
    lastRenderTime      \* Performance tracking

vars == <<commandQueue, commandProcessor, eventQueue, eventDispatcher, 
          networkStatus, retryCount, frontendState, backendState, 
          syncStatus, componentStates, renderQueue, lastRenderTime>>

\* TYPE INVARIANTS

TypeOK ==
    /\ commandQueue \in Seq(Commands)
    /\ commandProcessor \in {"idle", "processing", "error"}
    /\ eventQueue \in Seq(Events)
    /\ eventDispatcher \in {"idle", "dispatching", "retry", "failed"}
    /\ networkStatus \in {"connected", "disconnected", "reconnecting"}
    /\ retryCount \in 0..MaxRetries
    /\ frontendState \in [ComponentStates -> SUBSET ComponentStates]
    /\ backendState \in [ComponentStates -> SUBSET ComponentStates]
    /\ syncStatus \in {"synced", "syncing", "conflict", "error"}
    /\ componentStates \in [ComponentStates -> ComponentStates]
    /\ renderQueue \in Seq(ComponentStates)
    /\ lastRenderTime \in Nat

\* INITIAL STATE

Init ==
    /\ commandQueue = <<>>
    /\ commandProcessor = "idle"
    /\ eventQueue = <<>>
    /\ eventDispatcher = "idle"
    /\ networkStatus = "connected"
    /\ retryCount = 0
    /\ frontendState = [c \in ComponentStates |-> {}]
    /\ backendState = [c \in ComponentStates |-> {}]
    /\ syncStatus = "synced"
    /\ componentStates = [c \in ComponentStates |-> c]
    /\ renderQueue = <<>>
    /\ lastRenderTime = 0

\* COMMAND PROCESSING ACTIONS

\* Receive new SSE command from backend
ReceiveCommand ==
    /\ commandProcessor = "idle"
    /\ networkStatus = "connected"
    /\ Len(commandQueue) < MaxQueueSize
    /\ \E cmd \in Commands :
        commandQueue' = Append(commandQueue, cmd)
    /\ commandProcessor' = "processing"
    /\ UNCHANGED <<eventQueue, eventDispatcher, networkStatus, retryCount,
                   frontendState, backendState, syncStatus, componentStates,
                   renderQueue, lastRenderTime>>

\* Process command from queue
ProcessCommand ==
    /\ commandProcessor = "processing"
    /\ Len(commandQueue) > 0
    /\ LET cmd == Head(commandQueue) IN
        /\ commandQueue' = Tail(commandQueue)
        /\ \* Apply command to frontend state
           frontendState' = [frontendState EXCEPT ![cmd] = @ \cup {cmd}]
        /\ \* Update component states based on command
           componentStates' = [componentStates EXCEPT ![cmd] = cmd]
        /\ \* Add to render queue if needed  
           renderQueue' = IF ~(\E i \in 1..Len(renderQueue) : renderQueue[i] = cmd)
                         THEN Append(renderQueue, cmd)
                         ELSE renderQueue
    /\ commandProcessor' = IF Len(commandQueue') = 0 THEN "idle" ELSE "processing"
    /\ UNCHANGED <<eventQueue, eventDispatcher, networkStatus, retryCount,
                   backendState, syncStatus, lastRenderTime>>

\* EVENT DISPATCHING ACTIONS

\* User generates event (answer change, blur, etc.)
GenerateEvent ==
    /\ eventDispatcher = "idle"
    /\ Len(eventQueue) < MaxQueueSize
    /\ \E evt \in Events :
        eventQueue' = Append(eventQueue, evt)
    /\ eventDispatcher' = "dispatching"
    /\ UNCHANGED <<commandQueue, commandProcessor, networkStatus, retryCount,
                   frontendState, backendState, syncStatus, componentStates,
                   renderQueue, lastRenderTime>>

\* Dispatch event to backend
DispatchEvent ==
    /\ eventDispatcher = "dispatching"
    /\ Len(eventQueue) > 0
    /\ networkStatus = "connected"
    /\ LET evt == Head(eventQueue) IN
        /\ eventQueue' = Tail(eventQueue)
        /\ \* Update backend state optimistically
           backendState' = [backendState EXCEPT ![evt] = @ \cup {evt}]
        /\ retryCount' = 0
    /\ eventDispatcher' = IF Len(eventQueue') = 0 THEN "idle" ELSE "dispatching"
    /\ UNCHANGED <<commandQueue, commandProcessor, networkStatus,
                   frontendState, syncStatus, componentStates,
                   renderQueue, lastRenderTime>>

\* Retry failed event dispatch
RetryEvent ==
    /\ eventDispatcher = "retry"
    /\ retryCount < MaxRetries
    /\ networkStatus = "connected"
    /\ retryCount' = retryCount + 1
    /\ eventDispatcher' = "dispatching"
    /\ UNCHANGED <<commandQueue, commandProcessor, eventQueue, networkStatus,
                   frontendState, backendState, syncStatus, componentStates,
                   renderQueue, lastRenderTime>>

\* Handle dispatch failure
EventDispatchFailed ==
    /\ eventDispatcher = "dispatching"
    /\ networkStatus # "connected"
    /\ eventDispatcher' = IF retryCount < MaxRetries THEN "retry" ELSE "failed"
    /\ UNCHANGED <<commandQueue, commandProcessor, eventQueue, networkStatus,
                   retryCount, frontendState, backendState, syncStatus,
                   componentStates, renderQueue, lastRenderTime>>

\* STATE SYNCHRONIZATION ACTIONS

\* Detect state divergence
DetectStateDivergence ==
    /\ syncStatus = "synced"
    /\ \E c \in ComponentStates :
        frontendState[c] # backendState[c]
    /\ syncStatus' = "conflict"
    /\ UNCHANGED <<commandQueue, commandProcessor, eventQueue, eventDispatcher,
                   networkStatus, retryCount, frontendState, backendState,
                   componentStates, renderQueue, lastRenderTime>>

\* Resolve state conflict (backend authoritative)
ResolveStateConflict ==
    /\ syncStatus = "conflict"
    /\ frontendState' = backendState
    /\ syncStatus' = "synced"
    /\ \* Update component states to match backend
       componentStates' = [c \in ComponentStates |-> 
                          IF backendState[c] # {} THEN CHOOSE x \in backendState[c] : TRUE 
                          ELSE c]
    /\ UNCHANGED <<commandQueue, commandProcessor, eventQueue, eventDispatcher,
                   networkStatus, retryCount, backendState, renderQueue, lastRenderTime>>

\* UI RENDERING ACTIONS

\* Render pending components
RenderComponents ==
    /\ Len(renderQueue) > 0
    /\ LET comp == Head(renderQueue) IN
        /\ renderQueue' = Tail(renderQueue)
        /\ lastRenderTime' = lastRenderTime + 1
        /\ \* Component renders based on current state
           componentStates' = [componentStates EXCEPT ![comp] = 
                              IF frontendState[comp] # {} 
                              THEN CHOOSE x \in frontendState[comp] : TRUE
                              ELSE componentStates[comp]]
    /\ UNCHANGED <<commandQueue, commandProcessor, eventQueue, eventDispatcher,
                   networkStatus, retryCount, frontendState, backendState, syncStatus>>

\* NETWORK ACTIONS

NetworkDisconnect ==
    /\ networkStatus = "connected"
    /\ networkStatus' = "disconnected"
    /\ UNCHANGED <<commandQueue, commandProcessor, eventQueue, eventDispatcher,
                   retryCount, frontendState, backendState, syncStatus,
                   componentStates, renderQueue, lastRenderTime>>

NetworkReconnect ==
    /\ networkStatus = "disconnected"
    /\ networkStatus' = "connected"
    /\ syncStatus' = "syncing"
    /\ UNCHANGED <<commandQueue, commandProcessor, eventQueue, eventDispatcher,
                   retryCount, frontendState, backendState, componentStates,
                   renderQueue, lastRenderTime>>

\* SPECIFICATION

Next ==
    \/ ReceiveCommand
    \/ ProcessCommand
    \/ GenerateEvent
    \/ DispatchEvent
    \/ RetryEvent
    \/ EventDispatchFailed
    \/ DetectStateDivergence
    \/ ResolveStateConflict
    \/ RenderComponents
    \/ NetworkDisconnect
    \/ NetworkReconnect

Spec == Init /\ [][Next]_vars

\* SAFETY PROPERTIES

\* Command queue never overflows
CommandQueueSafety == Len(commandQueue) <= MaxQueueSize

\* Event queue never overflows  
EventQueueSafety == Len(eventQueue) <= MaxQueueSize

\* Retry count never exceeds maximum
RetryCountSafety == retryCount <= MaxRetries

\* State consistency after resolution
StateConsistency == 
    (syncStatus = "synced") => (frontendState = backendState)

\* No command processing when disconnected
NoProcessingWhenDisconnected ==
    (networkStatus = "disconnected") => (commandProcessor = "idle")

\* Component states are always valid
ComponentStateValidity ==
    \A c \in ComponentStates : componentStates[c] \in ComponentStates

\* LIVENESS PROPERTIES

\* Commands are eventually processed
CommandsEventuallyProcessed ==
    <>[]((Len(commandQueue) = 0) /\ (commandProcessor = "idle"))

\* Events are eventually dispatched or fail
EventsEventuallyProcessed ==
    <>[]((Len(eventQueue) = 0) /\ (eventDispatcher \in {"idle", "failed"}))

\* State conflicts are eventually resolved
StateConflictsResolved ==
    [](syncStatus = "conflict" ~> syncStatus = "synced")

\* UI rendering makes progress
RenderingProgress ==
    []<>(Len(renderQueue) = 0)

\* System recovers from network failures
NetworkRecovery ==
    [](networkStatus = "disconnected" ~> networkStatus = "connected")

====
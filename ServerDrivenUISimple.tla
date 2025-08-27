----------------------- MODULE ServerDrivenUISimple -----------------------

EXTENDS Integers, Sequences, TLC

CONSTANTS 
    Commands,        \* Set of available SSE commands  
    Events,          \* Set of user events
    MaxQueueSize     \* Maximum queue size

VARIABLES
    commandQueue,        \* Sequence of pending commands
    commandProcessor,    \* State of command processor: "idle" | "processing"
    eventQueue,          \* Pending user events  
    eventDispatcher,     \* State of event dispatcher
    networkStatus        \* Connection status

vars == <<commandQueue, commandProcessor, eventQueue, eventDispatcher, networkStatus>>

TypeOK ==
    /\ commandQueue \in Seq(Commands)
    /\ commandProcessor \in {"idle", "processing"} 
    /\ eventQueue \in Seq(Events)
    /\ eventDispatcher \in {"idle", "dispatching", "failed"}
    /\ networkStatus \in {"connected", "disconnected"}

Init ==
    /\ commandQueue = <<>>
    /\ commandProcessor = "idle"
    /\ eventQueue = <<>>
    /\ eventDispatcher = "idle" 
    /\ networkStatus = "connected"

\* Receive SSE command from backend
ReceiveCommand ==
    /\ commandProcessor = "idle"
    /\ networkStatus = "connected"
    /\ Len(commandQueue) < MaxQueueSize
    /\ \E cmd \in Commands :
        /\ commandQueue' = Append(commandQueue, cmd)
        /\ commandProcessor' = "processing"
    /\ UNCHANGED <<eventQueue, eventDispatcher, networkStatus>>

\* Process command from queue
ProcessCommand ==
    /\ commandProcessor = "processing"
    /\ Len(commandQueue) > 0
    /\ commandQueue' = Tail(commandQueue)
    /\ commandProcessor' = IF Len(commandQueue') = 0 THEN "idle" ELSE "processing"
    /\ UNCHANGED <<eventQueue, eventDispatcher, networkStatus>>

\* Generate user event
GenerateEvent ==
    /\ eventDispatcher = "idle"
    /\ networkStatus = "connected"
    /\ Len(eventQueue) < MaxQueueSize
    /\ \E evt \in Events :
        /\ eventQueue' = Append(eventQueue, evt)
        /\ eventDispatcher' = "dispatching"
    /\ UNCHANGED <<commandQueue, commandProcessor, networkStatus>>

\* Dispatch event to backend
DispatchEvent ==
    /\ eventDispatcher = "dispatching"
    /\ Len(eventQueue) > 0
    /\ networkStatus = "connected"
    /\ eventQueue' = Tail(eventQueue)
    /\ eventDispatcher' = IF Len(eventQueue') = 0 THEN "idle" ELSE "dispatching"
    /\ UNCHANGED <<commandQueue, commandProcessor, networkStatus>>

\* Handle dispatch failure
EventDispatchFailed ==
    /\ eventDispatcher = "dispatching"
    /\ networkStatus = "disconnected"
    /\ eventDispatcher' = "failed"
    /\ UNCHANGED <<commandQueue, commandProcessor, eventQueue, networkStatus>>

\* Network disconnect
NetworkDisconnect ==
    /\ networkStatus = "connected"
    /\ networkStatus' = "disconnected"
    /\ \* Stop processing when disconnected
       commandProcessor' = "idle"
    /\ \* Mark event dispatcher as failed if dispatching
       eventDispatcher' = IF eventDispatcher = "dispatching" THEN "failed" ELSE eventDispatcher
    /\ UNCHANGED <<commandQueue, eventQueue>>

\* Network reconnect
NetworkReconnect ==
    /\ networkStatus = "disconnected"
    /\ networkStatus' = "connected"
    /\ \* Reset failed event dispatcher and clear failed events
       eventDispatcher' = "idle"
    /\ \* Clear event queue on reconnect to prevent stale events
       eventQueue' = <<>>
    /\ UNCHANGED <<commandQueue, commandProcessor>>

Next ==
    \/ ReceiveCommand
    \/ ProcessCommand
    \/ GenerateEvent
    \/ DispatchEvent
    \/ EventDispatchFailed
    \/ NetworkDisconnect
    \/ NetworkReconnect

Spec == Init /\ [][Next]_vars /\ WF_vars(ProcessCommand) /\ WF_vars(DispatchEvent)

\* SAFETY PROPERTIES

\* Queues never overflow
QueueSafety == 
    /\ Len(commandQueue) <= MaxQueueSize
    /\ Len(eventQueue) <= MaxQueueSize

\* No processing when disconnected  
NoProcessingWhenDisconnected ==
    (networkStatus = "disconnected") => (commandProcessor = "idle")

\* Event dispatcher consistency
EventDispatcherConsistency ==
    ~(eventDispatcher = "dispatching" /\ networkStatus = "disconnected")

\* LIVENESS PROPERTIES

\* Commands are eventually processed
CommandsEventuallyProcessed ==
    <>[]((Len(commandQueue) = 0) /\ (commandProcessor = "idle"))

\* Events are eventually handled
EventsEventuallyHandled ==
    <>[]((Len(eventQueue) = 0) /\ (eventDispatcher \in {"idle", "failed"}))

\* System recovers from network failures
NetworkRecovery ==
    [](networkStatus = "disconnected" ~> networkStatus = "connected")

\* Deadlock freedom - system always has an enabled action
DeadlockFreedom ==
    []<>(ENABLED Next)

====
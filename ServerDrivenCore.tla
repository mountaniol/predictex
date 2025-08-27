----------------------- MODULE ServerDrivenCore -----------------------

EXTENDS Integers, Sequences, TLC

CONSTANTS 
    Commands,     \* Set of available SSE commands  
    Events,       \* Set of user events
    MaxQueue      \* Maximum queue size

VARIABLES
    cmdQueue,     \* Command queue from backend
    evtQueue,     \* Event queue to backend
    cmdState,     \* Command processor state
    evtState,     \* Event dispatcher state
    connected     \* Network connection status

vars == <<cmdQueue, evtQueue, cmdState, evtState, connected>>

TypeOK ==
    /\ cmdQueue \in Seq(Commands)
    /\ evtQueue \in Seq(Events)
    /\ cmdState \in {"idle", "busy"}
    /\ evtState \in {"idle", "busy", "error"}
    /\ connected \in BOOLEAN

Init ==
    /\ cmdQueue = <<>>
    /\ evtQueue = <<>>
    /\ cmdState = "idle"
    /\ evtState = "idle"
    /\ connected = TRUE

\* Receive command via SSE
RcvCmd ==
    /\ connected
    /\ Len(cmdQueue) < MaxQueue
    /\ \E cmd \in Commands :
        cmdQueue' = Append(cmdQueue, cmd)
    /\ UNCHANGED <<evtQueue, cmdState, evtState, connected>>

\* Process command
ProcCmd ==
    /\ cmdState = "idle"
    /\ Len(cmdQueue) > 0
    /\ cmdQueue' = Tail(cmdQueue)
    /\ cmdState' = "busy"
    /\ UNCHANGED <<evtQueue, evtState, connected>>

\* Complete command processing
CompleteCmd ==
    /\ cmdState = "busy"
    /\ cmdState' = "idle"
    /\ UNCHANGED <<cmdQueue, evtQueue, evtState, connected>>

\* Generate user event
GenEvt ==
    /\ connected
    /\ evtState = "idle"
    /\ Len(evtQueue) < MaxQueue
    /\ \E evt \in Events :
        evtQueue' = Append(evtQueue, evt)
    /\ evtState' = "busy"
    /\ UNCHANGED <<cmdQueue, cmdState, connected>>

\* Send event to backend
SendEvt ==
    /\ connected
    /\ evtState = "busy"
    /\ Len(evtQueue) > 0
    /\ evtQueue' = Tail(evtQueue)
    /\ evtState' = "idle"
    /\ UNCHANGED <<cmdQueue, cmdState, connected>>

\* Network disconnect
Disconnect ==
    /\ connected
    /\ connected' = FALSE
    /\ evtState' = IF evtState = "busy" THEN "error" ELSE evtState
    /\ UNCHANGED <<cmdQueue, evtQueue, cmdState>>

\* Network reconnect
Reconnect ==
    /\ ~connected
    /\ connected' = TRUE
    /\ evtState' = IF evtState = "error" THEN "idle" ELSE evtState
    /\ UNCHANGED <<cmdQueue, evtQueue, cmdState>>

Next ==
    \/ RcvCmd
    \/ ProcCmd
    \/ CompleteCmd
    \/ GenEvt
    \/ SendEvt
    \/ Disconnect
    \/ Reconnect

Spec == Init /\ [][Next]_vars /\ WF_vars(CompleteCmd) /\ WF_vars(SendEvt) /\ WF_vars(Reconnect)

\* SAFETY PROPERTIES

\* Queues bounded
QueueBounds == 
    /\ Len(cmdQueue) <= MaxQueue
    /\ Len(evtQueue) <= MaxQueue

\* No command processing when disconnected
NoOfflineProcessing ==
    ~connected => (evtState # "busy" \/ evtState = "error")

\* LIVENESS PROPERTIES

\* Commands eventually processed
CmdsProcessed ==
    []<>((Len(cmdQueue) = 0) /\ (cmdState = "idle"))

\* Events eventually handled
EvtsHandled ==
    []<>((Len(evtQueue) = 0) /\ (evtState \in {"idle", "error"}))

\* Network recovery
Recovery ==
    []<>(connected)

====
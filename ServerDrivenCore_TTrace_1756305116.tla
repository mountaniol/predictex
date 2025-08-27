---- MODULE ServerDrivenCore_TTrace_1756305116 ----
EXTENDS Sequences, TLCExt, ServerDrivenCore_TEConstants, ServerDrivenCore, Toolbox, Naturals, TLC

_expression ==
    LET ServerDrivenCore_TEExpression == INSTANCE ServerDrivenCore_TEExpression
    IN ServerDrivenCore_TEExpression!expression
----

_trace ==
    LET ServerDrivenCore_TETrace == INSTANCE ServerDrivenCore_TETrace
    IN ServerDrivenCore_TETrace!trace
----

_prop ==
    ~(([]<>(
            connected = (TRUE)
            /\
            evtQueue = (<<"ANSWER_CHANGE", "ANSWER_CHANGE", "SUBMIT">>)
            /\
            cmdQueue = (<<>>)
            /\
            evtState = ("idle")
            /\
            cmdState = ("busy")
    ))/\([]<>(
            connected = (TRUE)
            /\
            evtQueue = (<<"ANSWER_CHANGE", "ANSWER_CHANGE", "SUBMIT">>)
            /\
            cmdQueue = (<<"CLEAR_DATA">>)
            /\
            evtState = ("idle")
            /\
            cmdState = ("busy")
    )))
----

_init ==
    /\ connected = _TETrace[1].connected
    /\ cmdQueue = _TETrace[1].cmdQueue
    /\ cmdState = _TETrace[1].cmdState
    /\ evtQueue = _TETrace[1].evtQueue
    /\ evtState = _TETrace[1].evtState
----

_next ==
    /\ \E i,j \in DOMAIN _TETrace:
        /\ \/ /\ j = i + 1
              /\ i = TLCGet("level")
           \/ /\ i = _TTraceLassoEnd
              /\ j = _TTraceLassoStart
        /\ connected  = _TETrace[i].connected
        /\ connected' = _TETrace[j].connected
        /\ cmdQueue  = _TETrace[i].cmdQueue
        /\ cmdQueue' = _TETrace[j].cmdQueue
        /\ cmdState  = _TETrace[i].cmdState
        /\ cmdState' = _TETrace[j].cmdState
        /\ evtQueue  = _TETrace[i].evtQueue
        /\ evtQueue' = _TETrace[j].evtQueue
        /\ evtState  = _TETrace[i].evtState
        /\ evtState' = _TETrace[j].evtState

\* Uncomment the ASSUME below to write the states of the error trace
\* to the given file in Json format. Note that you can pass any tuple
\* to `JsonSerialize`. For example, a sub-sequence of _TETrace.
    \* ASSUME
    \*     LET J == INSTANCE Json
    \*         IN J!JsonSerialize("ServerDrivenCore_TTrace_1756305116.json", _TETrace)


_view ==
    <<connected, cmdQueue, cmdState, evtQueue, evtState, IF TLCGet("level") = _TTraceLassoEnd + 1 THEN _TTraceLassoStart ELSE TLCGet("level")>>
=============================================================================

 Note that you can extract this module `ServerDrivenCore_TEExpression`
  to a dedicated file to reuse `expression` (the module in the 
  dedicated `ServerDrivenCore_TEExpression.tla` file takes precedence 
  over the module `ServerDrivenCore_TEExpression` below).

---- MODULE ServerDrivenCore_TEExpression ----
EXTENDS Sequences, TLCExt, ServerDrivenCore_TEConstants, ServerDrivenCore, Toolbox, Naturals, TLC

expression == 
    [
        \* To hide variables of the `ServerDrivenCore` spec from the error trace,
        \* remove the variables below.  The trace will be written in the order
        \* of the fields of this record.
        connected |-> connected
        ,cmdQueue |-> cmdQueue
        ,cmdState |-> cmdState
        ,evtQueue |-> evtQueue
        ,evtState |-> evtState
        
        \* Put additional constant-, state-, and action-level expressions here:
        \* ,_stateNumber |-> _TEPosition
        \* ,_connectedUnchanged |-> connected = connected'
        
        \* Format the `connected` variable as Json value.
        \* ,_connectedJson |->
        \*     LET J == INSTANCE Json
        \*     IN J!ToJson(connected)
        
        \* Lastly, you may build expressions over arbitrary sets of states by
        \* leveraging the _TETrace operator.  For example, this is how to
        \* count the number of times a spec variable changed up to the current
        \* state in the trace.
        \* ,_connectedModCount |->
        \*     LET F[s \in DOMAIN _TETrace] ==
        \*         IF s = 1 THEN 0
        \*         ELSE IF _TETrace[s].connected # _TETrace[s-1].connected
        \*             THEN 1 + F[s-1] ELSE F[s-1]
        \*     IN F[_TEPosition - 1]
    ]

=============================================================================



Parsing and semantic processing can take forever if the trace below is long.
 In this case, it is advised to uncomment the module below to deserialize the
 trace from a generated binary file.

\*
\*---- MODULE ServerDrivenCore_TETrace ----
\*EXTENDS IOUtils, ServerDrivenCore_TEConstants, ServerDrivenCore, TLC
\*
\*trace == IODeserialize("ServerDrivenCore_TTrace_1756305116.bin", TRUE)
\*
\*=============================================================================
\*

---- MODULE ServerDrivenCore_TETrace ----
EXTENDS ServerDrivenCore_TEConstants, ServerDrivenCore, TLC

trace == 
    <<
    ([connected |-> TRUE,evtQueue |-> <<>>,cmdQueue |-> <<>>,evtState |-> "idle",cmdState |-> "idle"]),
    ([connected |-> TRUE,evtQueue |-> <<>>,cmdQueue |-> <<"CLEAR_DATA">>,evtState |-> "idle",cmdState |-> "idle"]),
    ([connected |-> TRUE,evtQueue |-> <<>>,cmdQueue |-> <<"CLEAR_DATA", "CLEAR_DATA">>,evtState |-> "idle",cmdState |-> "idle"]),
    ([connected |-> TRUE,evtQueue |-> <<>>,cmdQueue |-> <<"CLEAR_DATA">>,evtState |-> "idle",cmdState |-> "busy"]),
    ([connected |-> TRUE,evtQueue |-> <<"ANSWER_CHANGE">>,cmdQueue |-> <<"CLEAR_DATA">>,evtState |-> "busy",cmdState |-> "busy"]),
    ([connected |-> FALSE,evtQueue |-> <<"ANSWER_CHANGE">>,cmdQueue |-> <<"CLEAR_DATA">>,evtState |-> "error",cmdState |-> "busy"]),
    ([connected |-> TRUE,evtQueue |-> <<"ANSWER_CHANGE">>,cmdQueue |-> <<"CLEAR_DATA">>,evtState |-> "idle",cmdState |-> "busy"]),
    ([connected |-> TRUE,evtQueue |-> <<"ANSWER_CHANGE", "ANSWER_CHANGE">>,cmdQueue |-> <<"CLEAR_DATA">>,evtState |-> "busy",cmdState |-> "busy"]),
    ([connected |-> FALSE,evtQueue |-> <<"ANSWER_CHANGE", "ANSWER_CHANGE">>,cmdQueue |-> <<"CLEAR_DATA">>,evtState |-> "error",cmdState |-> "busy"]),
    ([connected |-> TRUE,evtQueue |-> <<"ANSWER_CHANGE", "ANSWER_CHANGE">>,cmdQueue |-> <<"CLEAR_DATA">>,evtState |-> "idle",cmdState |-> "busy"]),
    ([connected |-> TRUE,evtQueue |-> <<"ANSWER_CHANGE", "ANSWER_CHANGE", "SUBMIT">>,cmdQueue |-> <<"CLEAR_DATA">>,evtState |-> "busy",cmdState |-> "busy"]),
    ([connected |-> FALSE,evtQueue |-> <<"ANSWER_CHANGE", "ANSWER_CHANGE", "SUBMIT">>,cmdQueue |-> <<"CLEAR_DATA">>,evtState |-> "error",cmdState |-> "busy"]),
    ([connected |-> TRUE,evtQueue |-> <<"ANSWER_CHANGE", "ANSWER_CHANGE", "SUBMIT">>,cmdQueue |-> <<"CLEAR_DATA">>,evtState |-> "idle",cmdState |-> "busy"]),
    ([connected |-> TRUE,evtQueue |-> <<"ANSWER_CHANGE", "ANSWER_CHANGE", "SUBMIT">>,cmdQueue |-> <<"CLEAR_DATA">>,evtState |-> "idle",cmdState |-> "idle"]),
    ([connected |-> TRUE,evtQueue |-> <<"ANSWER_CHANGE", "ANSWER_CHANGE", "SUBMIT">>,cmdQueue |-> <<>>,evtState |-> "idle",cmdState |-> "busy"])
    >>
----


=============================================================================

---- MODULE ServerDrivenCore_TEConstants ----
EXTENDS ServerDrivenCore

CONSTANTS _TTraceLassoStart, _TTraceLassoEnd

=============================================================================

---- CONFIG ServerDrivenCore_TTrace_1756305116 ----
CONSTANTS
    Commands = { "UPDATE_SCORE" , "UPDATE_STATE" , "CLEAR_DATA" }
    Events = { "ANSWER_CHANGE" , "SUBMIT" }
    MaxQueue = 3
_TTraceLassoStart = 13
_TTraceLassoEnd = 15

PROPERTY
    _prop

CHECK_DEADLOCK
    \* CHECK_DEADLOCK off because of PROPERTY or INVARIANT above.
    FALSE

INIT
    _init

NEXT
    _next

VIEW
    _view

CONSTANT
    _TETrace <- _trace

ALIAS
    _expression
=============================================================================
\* Generated on Wed Aug 27 16:31:57 CEST 2025
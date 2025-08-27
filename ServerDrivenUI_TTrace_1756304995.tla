---- MODULE ServerDrivenUI_TTrace_1756304995 ----
EXTENDS Sequences, TLCExt, Toolbox, Naturals, TLC, ServerDrivenUI

_expression ==
    LET ServerDrivenUI_TEExpression == INSTANCE ServerDrivenUI_TEExpression
    IN ServerDrivenUI_TEExpression!expression
----

_trace ==
    LET ServerDrivenUI_TETrace == INSTANCE ServerDrivenUI_TETrace
    IN ServerDrivenUI_TETrace!trace
----

_inv ==
    ~(
        TLCGet("level") = Len(_TETrace)
        /\
        eventQueue = (<<>>)
        /\
        renderQueue = (<<"UPDATE_SCORE">>)
        /\
        commandQueue = (<<>>)
        /\
        frontendState = ([question1 |-> {}, question2 |-> {}, question3 |-> {}, summary |-> {}])
        /\
        retryCount = (0)
        /\
        backendState = ([question1 |-> {}, question2 |-> {}, question3 |-> {}, summary |-> {}])
        /\
        networkStatus = ("connected")
        /\
        componentStates = ([question1 |-> "question1", question2 |-> "question2", question3 |-> "question3", summary |-> "summary"])
        /\
        lastRenderTime = (0)
        /\
        commandProcessor = ("idle")
        /\
        syncStatus = ("synced")
        /\
        eventDispatcher = ("idle")
    )
----

_init ==
    /\ frontendState = _TETrace[1].frontendState
    /\ componentStates = _TETrace[1].componentStates
    /\ commandProcessor = _TETrace[1].commandProcessor
    /\ eventQueue = _TETrace[1].eventQueue
    /\ syncStatus = _TETrace[1].syncStatus
    /\ backendState = _TETrace[1].backendState
    /\ eventDispatcher = _TETrace[1].eventDispatcher
    /\ networkStatus = _TETrace[1].networkStatus
    /\ renderQueue = _TETrace[1].renderQueue
    /\ retryCount = _TETrace[1].retryCount
    /\ commandQueue = _TETrace[1].commandQueue
    /\ lastRenderTime = _TETrace[1].lastRenderTime
----

_next ==
    /\ \E i,j \in DOMAIN _TETrace:
        /\ \/ /\ j = i + 1
              /\ i = TLCGet("level")
        /\ frontendState  = _TETrace[i].frontendState
        /\ frontendState' = _TETrace[j].frontendState
        /\ componentStates  = _TETrace[i].componentStates
        /\ componentStates' = _TETrace[j].componentStates
        /\ commandProcessor  = _TETrace[i].commandProcessor
        /\ commandProcessor' = _TETrace[j].commandProcessor
        /\ eventQueue  = _TETrace[i].eventQueue
        /\ eventQueue' = _TETrace[j].eventQueue
        /\ syncStatus  = _TETrace[i].syncStatus
        /\ syncStatus' = _TETrace[j].syncStatus
        /\ backendState  = _TETrace[i].backendState
        /\ backendState' = _TETrace[j].backendState
        /\ eventDispatcher  = _TETrace[i].eventDispatcher
        /\ eventDispatcher' = _TETrace[j].eventDispatcher
        /\ networkStatus  = _TETrace[i].networkStatus
        /\ networkStatus' = _TETrace[j].networkStatus
        /\ renderQueue  = _TETrace[i].renderQueue
        /\ renderQueue' = _TETrace[j].renderQueue
        /\ retryCount  = _TETrace[i].retryCount
        /\ retryCount' = _TETrace[j].retryCount
        /\ commandQueue  = _TETrace[i].commandQueue
        /\ commandQueue' = _TETrace[j].commandQueue
        /\ lastRenderTime  = _TETrace[i].lastRenderTime
        /\ lastRenderTime' = _TETrace[j].lastRenderTime

\* Uncomment the ASSUME below to write the states of the error trace
\* to the given file in Json format. Note that you can pass any tuple
\* to `JsonSerialize`. For example, a sub-sequence of _TETrace.
    \* ASSUME
    \*     LET J == INSTANCE Json
    \*         IN J!JsonSerialize("ServerDrivenUI_TTrace_1756304995.json", _TETrace)

=============================================================================

 Note that you can extract this module `ServerDrivenUI_TEExpression`
  to a dedicated file to reuse `expression` (the module in the 
  dedicated `ServerDrivenUI_TEExpression.tla` file takes precedence 
  over the module `ServerDrivenUI_TEExpression` below).

---- MODULE ServerDrivenUI_TEExpression ----
EXTENDS Sequences, TLCExt, Toolbox, Naturals, TLC, ServerDrivenUI

expression == 
    [
        \* To hide variables of the `ServerDrivenUI` spec from the error trace,
        \* remove the variables below.  The trace will be written in the order
        \* of the fields of this record.
        frontendState |-> frontendState
        ,componentStates |-> componentStates
        ,commandProcessor |-> commandProcessor
        ,eventQueue |-> eventQueue
        ,syncStatus |-> syncStatus
        ,backendState |-> backendState
        ,eventDispatcher |-> eventDispatcher
        ,networkStatus |-> networkStatus
        ,renderQueue |-> renderQueue
        ,retryCount |-> retryCount
        ,commandQueue |-> commandQueue
        ,lastRenderTime |-> lastRenderTime
        
        \* Put additional constant-, state-, and action-level expressions here:
        \* ,_stateNumber |-> _TEPosition
        \* ,_frontendStateUnchanged |-> frontendState = frontendState'
        
        \* Format the `frontendState` variable as Json value.
        \* ,_frontendStateJson |->
        \*     LET J == INSTANCE Json
        \*     IN J!ToJson(frontendState)
        
        \* Lastly, you may build expressions over arbitrary sets of states by
        \* leveraging the _TETrace operator.  For example, this is how to
        \* count the number of times a spec variable changed up to the current
        \* state in the trace.
        \* ,_frontendStateModCount |->
        \*     LET F[s \in DOMAIN _TETrace] ==
        \*         IF s = 1 THEN 0
        \*         ELSE IF _TETrace[s].frontendState # _TETrace[s-1].frontendState
        \*             THEN 1 + F[s-1] ELSE F[s-1]
        \*     IN F[_TEPosition - 1]
    ]

=============================================================================



Parsing and semantic processing can take forever if the trace below is long.
 In this case, it is advised to uncomment the module below to deserialize the
 trace from a generated binary file.

\*
\*---- MODULE ServerDrivenUI_TETrace ----
\*EXTENDS IOUtils, TLC, ServerDrivenUI
\*
\*trace == IODeserialize("ServerDrivenUI_TTrace_1756304995.bin", TRUE)
\*
\*=============================================================================
\*

---- MODULE ServerDrivenUI_TETrace ----
EXTENDS TLC, ServerDrivenUI

trace == 
    <<
    ([eventQueue |-> <<>>,renderQueue |-> <<>>,commandQueue |-> <<>>,frontendState |-> [question1 |-> {}, question2 |-> {}, question3 |-> {}, summary |-> {}],retryCount |-> 0,backendState |-> [question1 |-> {}, question2 |-> {}, question3 |-> {}, summary |-> {}],networkStatus |-> "connected",componentStates |-> [question1 |-> "question1", question2 |-> "question2", question3 |-> "question3", summary |-> "summary"],lastRenderTime |-> 0,commandProcessor |-> "idle",syncStatus |-> "synced",eventDispatcher |-> "idle"]),
    ([eventQueue |-> <<>>,renderQueue |-> <<>>,commandQueue |-> <<"UPDATE_SCORE">>,frontendState |-> [question1 |-> {}, question2 |-> {}, question3 |-> {}, summary |-> {}],retryCount |-> 0,backendState |-> [question1 |-> {}, question2 |-> {}, question3 |-> {}, summary |-> {}],networkStatus |-> "connected",componentStates |-> [question1 |-> "question1", question2 |-> "question2", question3 |-> "question3", summary |-> "summary"],lastRenderTime |-> 0,commandProcessor |-> "processing",syncStatus |-> "synced",eventDispatcher |-> "idle"]),
    ([eventQueue |-> <<>>,renderQueue |-> <<"UPDATE_SCORE">>,commandQueue |-> <<>>,frontendState |-> [question1 |-> {}, question2 |-> {}, question3 |-> {}, summary |-> {}],retryCount |-> 0,backendState |-> [question1 |-> {}, question2 |-> {}, question3 |-> {}, summary |-> {}],networkStatus |-> "connected",componentStates |-> [question1 |-> "question1", question2 |-> "question2", question3 |-> "question3", summary |-> "summary"],lastRenderTime |-> 0,commandProcessor |-> "idle",syncStatus |-> "synced",eventDispatcher |-> "idle"])
    >>
----


=============================================================================

---- CONFIG ServerDrivenUI_TTrace_1756304995 ----
CONSTANTS
    Commands = { "UPDATE_SCORE" , "UPDATE_STATE" , "SHOW_ERROR" , "CLEAR_DATA" }
    Events = { "ANSWER_CHANGE" , "ANSWER_BLUR" , "SUBMIT" , "NAVIGATE" }
    ComponentStates = { "question1" , "question2" , "question3" , "summary" }
    MaxQueueSize = 10
    MaxRetries = 3

INVARIANT
    _inv

CHECK_DEADLOCK
    \* CHECK_DEADLOCK off because of PROPERTY or INVARIANT above.
    FALSE

INIT
    _init

NEXT
    _next

CONSTANT
    _TETrace <- _trace

ALIAS
    _expression
=============================================================================
\* Generated on Wed Aug 27 16:29:56 CEST 2025
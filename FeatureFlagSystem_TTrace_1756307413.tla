---- MODULE FeatureFlagSystem_TTrace_1756307413 ----
EXTENDS Sequences, TLCExt, FeatureFlagSystem, Toolbox, Naturals, TLC

_expression ==
    LET FeatureFlagSystem_TEExpression == INSTANCE FeatureFlagSystem_TEExpression
    IN FeatureFlagSystem_TEExpression!expression
----

_trace ==
    LET FeatureFlagSystem_TETrace == INSTANCE FeatureFlagSystem_TETrace
    IN FeatureFlagSystem_TETrace!trace
----

_inv ==
    ~(
        TLCGet("level") = Len(_TETrace)
        /\
        sessionState = (<<[mode |-> "thick", timestamp |-> 0], [mode |-> "thick", timestamp |-> 0], [mode |-> "thick", timestamp |-> 0], [mode |-> "thick", timestamp |-> 0], [mode |-> "thick", timestamp |-> 0]>>)
        /\
        flagConfig = ([server_driven_ui |-> [percentage |-> 4, overrides |-> {}, enabled |-> TRUE], new_feature |-> [percentage |-> 1, overrides |-> {}, enabled |-> TRUE], beta_feature |-> [percentage |-> 0, overrides |-> {}, enabled |-> TRUE]])
        /\
        rolloutState = ([server_driven_ui |-> 4, new_feature |-> 1, beta_feature |-> 0])
        /\
        userAssignments = ((<<1, "server_driven_ui">> :> FALSE @@ <<1, "new_feature">> :> FALSE @@ <<1, "beta_feature">> :> FALSE @@ <<2, "server_driven_ui">> :> FALSE @@ <<2, "new_feature">> :> FALSE @@ <<2, "beta_feature">> :> FALSE @@ <<3, "server_driven_ui">> :> FALSE @@ <<3, "new_feature">> :> FALSE @@ <<3, "beta_feature">> :> FALSE @@ <<4, "server_driven_ui">> :> FALSE @@ <<4, "new_feature">> :> FALSE @@ <<4, "beta_feature">> :> FALSE @@ <<5, "server_driven_ui">> :> FALSE @@ <<5, "new_feature">> :> FALSE @@ <<5, "beta_feature">> :> FALSE))
    )
----

_init ==
    /\ userAssignments = _TETrace[1].userAssignments
    /\ rolloutState = _TETrace[1].rolloutState
    /\ sessionState = _TETrace[1].sessionState
    /\ flagConfig = _TETrace[1].flagConfig
----

_next ==
    /\ \E i,j \in DOMAIN _TETrace:
        /\ \/ /\ j = i + 1
              /\ i = TLCGet("level")
        /\ userAssignments  = _TETrace[i].userAssignments
        /\ userAssignments' = _TETrace[j].userAssignments
        /\ rolloutState  = _TETrace[i].rolloutState
        /\ rolloutState' = _TETrace[j].rolloutState
        /\ sessionState  = _TETrace[i].sessionState
        /\ sessionState' = _TETrace[j].sessionState
        /\ flagConfig  = _TETrace[i].flagConfig
        /\ flagConfig' = _TETrace[j].flagConfig

\* Uncomment the ASSUME below to write the states of the error trace
\* to the given file in Json format. Note that you can pass any tuple
\* to `JsonSerialize`. For example, a sub-sequence of _TETrace.
    \* ASSUME
    \*     LET J == INSTANCE Json
    \*         IN J!JsonSerialize("FeatureFlagSystem_TTrace_1756307413.json", _TETrace)

=============================================================================

 Note that you can extract this module `FeatureFlagSystem_TEExpression`
  to a dedicated file to reuse `expression` (the module in the 
  dedicated `FeatureFlagSystem_TEExpression.tla` file takes precedence 
  over the module `FeatureFlagSystem_TEExpression` below).

---- MODULE FeatureFlagSystem_TEExpression ----
EXTENDS Sequences, TLCExt, FeatureFlagSystem, Toolbox, Naturals, TLC

expression == 
    [
        \* To hide variables of the `FeatureFlagSystem` spec from the error trace,
        \* remove the variables below.  The trace will be written in the order
        \* of the fields of this record.
        userAssignments |-> userAssignments
        ,rolloutState |-> rolloutState
        ,sessionState |-> sessionState
        ,flagConfig |-> flagConfig
        
        \* Put additional constant-, state-, and action-level expressions here:
        \* ,_stateNumber |-> _TEPosition
        \* ,_userAssignmentsUnchanged |-> userAssignments = userAssignments'
        
        \* Format the `userAssignments` variable as Json value.
        \* ,_userAssignmentsJson |->
        \*     LET J == INSTANCE Json
        \*     IN J!ToJson(userAssignments)
        
        \* Lastly, you may build expressions over arbitrary sets of states by
        \* leveraging the _TETrace operator.  For example, this is how to
        \* count the number of times a spec variable changed up to the current
        \* state in the trace.
        \* ,_userAssignmentsModCount |->
        \*     LET F[s \in DOMAIN _TETrace] ==
        \*         IF s = 1 THEN 0
        \*         ELSE IF _TETrace[s].userAssignments # _TETrace[s-1].userAssignments
        \*             THEN 1 + F[s-1] ELSE F[s-1]
        \*     IN F[_TEPosition - 1]
    ]

=============================================================================



Parsing and semantic processing can take forever if the trace below is long.
 In this case, it is advised to uncomment the module below to deserialize the
 trace from a generated binary file.

\*
\*---- MODULE FeatureFlagSystem_TETrace ----
\*EXTENDS IOUtils, FeatureFlagSystem, TLC
\*
\*trace == IODeserialize("FeatureFlagSystem_TTrace_1756307413.bin", TRUE)
\*
\*=============================================================================
\*

---- MODULE FeatureFlagSystem_TETrace ----
EXTENDS FeatureFlagSystem, TLC

trace == 
    <<
    ([sessionState |-> <<[mode |-> "thick", timestamp |-> 0], [mode |-> "thick", timestamp |-> 0], [mode |-> "thick", timestamp |-> 0], [mode |-> "thick", timestamp |-> 0], [mode |-> "thick", timestamp |-> 0]>>,flagConfig |-> [server_driven_ui |-> [percentage |-> 0, overrides |-> {}, enabled |-> TRUE], new_feature |-> [percentage |-> 0, overrides |-> {}, enabled |-> TRUE], beta_feature |-> [percentage |-> 0, overrides |-> {}, enabled |-> TRUE]],rolloutState |-> [server_driven_ui |-> 0, new_feature |-> 0, beta_feature |-> 0],userAssignments |-> (<<1, "server_driven_ui">> :> FALSE @@ <<1, "new_feature">> :> FALSE @@ <<1, "beta_feature">> :> FALSE @@ <<2, "server_driven_ui">> :> FALSE @@ <<2, "new_feature">> :> FALSE @@ <<2, "beta_feature">> :> FALSE @@ <<3, "server_driven_ui">> :> FALSE @@ <<3, "new_feature">> :> FALSE @@ <<3, "beta_feature">> :> FALSE @@ <<4, "server_driven_ui">> :> FALSE @@ <<4, "new_feature">> :> FALSE @@ <<4, "beta_feature">> :> FALSE @@ <<5, "server_driven_ui">> :> FALSE @@ <<5, "new_feature">> :> FALSE @@ <<5, "beta_feature">> :> FALSE)]),
    ([sessionState |-> <<[mode |-> "thick", timestamp |-> 0], [mode |-> "thick", timestamp |-> 0], [mode |-> "thick", timestamp |-> 0], [mode |-> "thick", timestamp |-> 0], [mode |-> "thick", timestamp |-> 0]>>,flagConfig |-> [server_driven_ui |-> [percentage |-> 1, overrides |-> {}, enabled |-> TRUE], new_feature |-> [percentage |-> 0, overrides |-> {}, enabled |-> TRUE], beta_feature |-> [percentage |-> 0, overrides |-> {}, enabled |-> TRUE]],rolloutState |-> [server_driven_ui |-> 1, new_feature |-> 0, beta_feature |-> 0],userAssignments |-> (<<1, "server_driven_ui">> :> FALSE @@ <<1, "new_feature">> :> FALSE @@ <<1, "beta_feature">> :> FALSE @@ <<2, "server_driven_ui">> :> FALSE @@ <<2, "new_feature">> :> FALSE @@ <<2, "beta_feature">> :> FALSE @@ <<3, "server_driven_ui">> :> FALSE @@ <<3, "new_feature">> :> FALSE @@ <<3, "beta_feature">> :> FALSE @@ <<4, "server_driven_ui">> :> FALSE @@ <<4, "new_feature">> :> FALSE @@ <<4, "beta_feature">> :> FALSE @@ <<5, "server_driven_ui">> :> FALSE @@ <<5, "new_feature">> :> FALSE @@ <<5, "beta_feature">> :> FALSE)]),
    ([sessionState |-> <<[mode |-> "thick", timestamp |-> 0], [mode |-> "thick", timestamp |-> 0], [mode |-> "thick", timestamp |-> 0], [mode |-> "thick", timestamp |-> 0], [mode |-> "thick", timestamp |-> 0]>>,flagConfig |-> [server_driven_ui |-> [percentage |-> 1, overrides |-> {}, enabled |-> TRUE], new_feature |-> [percentage |-> 1, overrides |-> {}, enabled |-> TRUE], beta_feature |-> [percentage |-> 0, overrides |-> {}, enabled |-> TRUE]],rolloutState |-> [server_driven_ui |-> 1, new_feature |-> 1, beta_feature |-> 0],userAssignments |-> (<<1, "server_driven_ui">> :> FALSE @@ <<1, "new_feature">> :> FALSE @@ <<1, "beta_feature">> :> FALSE @@ <<2, "server_driven_ui">> :> FALSE @@ <<2, "new_feature">> :> FALSE @@ <<2, "beta_feature">> :> FALSE @@ <<3, "server_driven_ui">> :> FALSE @@ <<3, "new_feature">> :> FALSE @@ <<3, "beta_feature">> :> FALSE @@ <<4, "server_driven_ui">> :> FALSE @@ <<4, "new_feature">> :> FALSE @@ <<4, "beta_feature">> :> FALSE @@ <<5, "server_driven_ui">> :> FALSE @@ <<5, "new_feature">> :> FALSE @@ <<5, "beta_feature">> :> FALSE)]),
    ([sessionState |-> <<[mode |-> "thick", timestamp |-> 0], [mode |-> "thick", timestamp |-> 0], [mode |-> "thick", timestamp |-> 0], [mode |-> "thick", timestamp |-> 0], [mode |-> "thick", timestamp |-> 0]>>,flagConfig |-> [server_driven_ui |-> [percentage |-> 2, overrides |-> {}, enabled |-> TRUE], new_feature |-> [percentage |-> 1, overrides |-> {}, enabled |-> TRUE], beta_feature |-> [percentage |-> 0, overrides |-> {}, enabled |-> TRUE]],rolloutState |-> [server_driven_ui |-> 2, new_feature |-> 1, beta_feature |-> 0],userAssignments |-> (<<1, "server_driven_ui">> :> FALSE @@ <<1, "new_feature">> :> FALSE @@ <<1, "beta_feature">> :> FALSE @@ <<2, "server_driven_ui">> :> FALSE @@ <<2, "new_feature">> :> FALSE @@ <<2, "beta_feature">> :> FALSE @@ <<3, "server_driven_ui">> :> FALSE @@ <<3, "new_feature">> :> FALSE @@ <<3, "beta_feature">> :> FALSE @@ <<4, "server_driven_ui">> :> FALSE @@ <<4, "new_feature">> :> FALSE @@ <<4, "beta_feature">> :> FALSE @@ <<5, "server_driven_ui">> :> FALSE @@ <<5, "new_feature">> :> FALSE @@ <<5, "beta_feature">> :> FALSE)]),
    ([sessionState |-> <<[mode |-> "thick", timestamp |-> 0], [mode |-> "thick", timestamp |-> 0], [mode |-> "thick", timestamp |-> 0], [mode |-> "thick", timestamp |-> 0], [mode |-> "thick", timestamp |-> 0]>>,flagConfig |-> [server_driven_ui |-> [percentage |-> 4, overrides |-> {}, enabled |-> TRUE], new_feature |-> [percentage |-> 1, overrides |-> {}, enabled |-> TRUE], beta_feature |-> [percentage |-> 0, overrides |-> {}, enabled |-> TRUE]],rolloutState |-> [server_driven_ui |-> 4, new_feature |-> 1, beta_feature |-> 0],userAssignments |-> (<<1, "server_driven_ui">> :> FALSE @@ <<1, "new_feature">> :> FALSE @@ <<1, "beta_feature">> :> FALSE @@ <<2, "server_driven_ui">> :> FALSE @@ <<2, "new_feature">> :> FALSE @@ <<2, "beta_feature">> :> FALSE @@ <<3, "server_driven_ui">> :> FALSE @@ <<3, "new_feature">> :> FALSE @@ <<3, "beta_feature">> :> FALSE @@ <<4, "server_driven_ui">> :> FALSE @@ <<4, "new_feature">> :> FALSE @@ <<4, "beta_feature">> :> FALSE @@ <<5, "server_driven_ui">> :> FALSE @@ <<5, "new_feature">> :> FALSE @@ <<5, "beta_feature">> :> FALSE)])
    >>
----


=============================================================================

---- CONFIG FeatureFlagSystem_TTrace_1756307413 ----
CONSTANTS
    Users = { 1 , 2 , 3 , 4 , 5 }
    FeatureFlags = { "server_driven_ui" , "new_feature" , "beta_feature" }
    MaxPercentage = 100

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
\* Generated on Wed Aug 27 17:10:14 CEST 2025
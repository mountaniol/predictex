---- MODULE FeatureFlagSystem ----
EXTENDS TLC, Integers, Sequences, FiniteSets

CONSTANTS 
    Users,           \* Set of user IDs
    FeatureFlags,    \* Set of feature flag names
    MaxPercentage    \* Maximum rollout percentage (100)

VARIABLES
    flagConfig,      \* Configuration for each flag
    userAssignments, \* Current user assignments
    rolloutState,    \* Current rollout state
    sessionState     \* User session tracking

vars == <<flagConfig, userAssignments, rolloutState, sessionState>>

TypeInvariant == 
    /\ flagConfig \in [FeatureFlags -> [percentage: 0..MaxPercentage, 
                                        overrides: SUBSET Users,
                                        enabled: BOOLEAN]]
    /\ userAssignments \in [Users \X FeatureFlags -> BOOLEAN]
    /\ rolloutState \in [FeatureFlags -> 0..MaxPercentage]
    /\ sessionState \in [Users -> [mode: {"thick", "thin"}, timestamp: Nat]]

\* Hash function for consistent user assignment
UserHash(user, flag) == 
    (user + LET hash == CHOOSE x \in 1..100 : x = ((user * 37 + 13) % 100) + 1
     IN hash) % 100

\* Feature flag evaluation logic
IsFeatureEnabled(user, flag) ==
    LET config == flagConfig[flag]
        userHash == UserHash(user, flag)
        inOverride == user \in config.overrides
        belowThreshold == userHash <= config.percentage
    IN 
        /\ config.enabled
        /\ (inOverride \/ belowThreshold)

\* Initialize system state
Init ==
    /\ flagConfig = [f \in FeatureFlags |-> 
                     [percentage |-> 0, overrides |-> {}, enabled |-> TRUE]]
    /\ userAssignments = [u \in Users, f \in FeatureFlags |-> FALSE]
    /\ rolloutState = [f \in FeatureFlags |-> 0]
    /\ sessionState = [u \in Users |-> [mode |-> "thick", timestamp |-> 0]]

\* Update feature flag configuration
UpdateFeatureFlag(flag, newPercentage, newOverrides) ==
    /\ flag \in FeatureFlags
    /\ newPercentage \in 0..MaxPercentage
    /\ newOverrides \in SUBSET Users
    /\ flagConfig' = [flagConfig EXCEPT ![flag].percentage = newPercentage,
                                        ![flag].overrides = newOverrides]
    /\ rolloutState' = [rolloutState EXCEPT ![flag] = newPercentage]
    /\ UNCHANGED <<userAssignments, sessionState>>

\* User session mode assignment
AssignUserMode(user) ==
    LET serverDrivenFlag == "server_driven_ui"
        enabled == IsFeatureEnabled(user, serverDrivenFlag)
        newMode == IF enabled THEN "thin" ELSE "thick"
    IN
        /\ user \in Users
        /\ userAssignments' = [userAssignments EXCEPT ![user, serverDrivenFlag] = enabled]
        /\ sessionState' = [sessionState EXCEPT ![user].mode = newMode,
                                                ![user].timestamp = rolloutState[serverDrivenFlag]]
        /\ UNCHANGED <<flagConfig, rolloutState>>

\* Gradual rollout action
GradualRollout(flag, increment) ==
    /\ flag \in FeatureFlags
    /\ increment \in 1..10
    /\ rolloutState[flag] + increment <= MaxPercentage
    /\ flagConfig' = [flagConfig EXCEPT ![flag].percentage = rolloutState[flag] + increment]
    /\ rolloutState' = [rolloutState EXCEPT ![flag] = rolloutState[flag] + increment]
    /\ UNCHANGED <<userAssignments, sessionState>>

\* Emergency rollback
EmergencyRollback(flag) ==
    /\ flag \in FeatureFlags
    /\ flagConfig' = [flagConfig EXCEPT ![flag].percentage = 0]
    /\ rolloutState' = [rolloutState EXCEPT ![flag] = 0]
    /\ UNCHANGED <<userAssignments, sessionState>>

\* Next state transitions
Next ==
    \/ \E flag \in FeatureFlags, pct \in 0..MaxPercentage, overrides \in SUBSET Users :
        UpdateFeatureFlag(flag, pct, overrides)
    \/ \E user \in Users : AssignUserMode(user)
    \/ \E flag \in FeatureFlags, inc \in 1..10 : GradualRollout(flag, inc)
    \/ \E flag \in FeatureFlags : EmergencyRollback(flag)

\* System specification
Spec == Init /\ [][Next]_vars

\* Safety properties
ConsistencyInvariant ==
    \A user \in Users, flag \in FeatureFlags :
        userAssignments[user, flag] = IsFeatureEnabled(user, flag)

SessionConsistency ==
    \A user \in Users :
        LET serverDrivenEnabled == IsFeatureEnabled(user, "server_driven_ui")
            expectedMode == IF serverDrivenEnabled THEN "thin" ELSE "thick"
        IN sessionState[user].mode = expectedMode

RolloutMonotonicity ==
    \A flag \in FeatureFlags :
        rolloutState[flag] >= 0 /\ rolloutState[flag] <= MaxPercentage

\* Liveness properties  
EventualRollout ==
    <>(\E flag \in FeatureFlags : rolloutState[flag] = MaxPercentage)

\* Hash distribution uniformity (approximation)
HashDistributionProperty ==
    \A flag \in FeatureFlags :
        rolloutState[flag] > 0 =>
            Cardinality({user \in Users : UserHash(user, flag) <= rolloutState[flag]}) 
            >= (Cardinality(Users) * rolloutState[flag]) \div MaxPercentage

====
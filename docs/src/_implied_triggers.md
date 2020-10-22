If no triggers are explicitly defined for a rule, they may be
 implied from the variables used in conditions. For example, the variable `behind` could change when the triggers
  `pr_created` and `pr_updated` are activated, so if the rule doesn't explicitly set a trigger, these two are added
   automatically.
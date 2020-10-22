# Triggers

Triggers are events that prompt the evaluation of a rule. They could be events such as a pull request being opened or
 updated with new commits.
 
{% include '_implied_triggers.md' %}
   
## Available triggers

{% for trigger in rule_triggers %}
* `{{ trigger.key}}` - {{ trigger.label }}
{% endfor %}


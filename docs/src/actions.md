# Actions

Actions are steps the rule should take once all conditions are satisfied.
 
## Available actions

{% for var in rule_actions %}
* `{{ var.key}}` - {{ var.label }}
{% endfor %}


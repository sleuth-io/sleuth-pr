# Conditions

Conditions are expressions that determine if the rule should be executed or not. They are composed of a simplified
 expression language that supports many common operations such as equals, greater than, or even pattern matching.
 
If the left value of an expression is a list, then the operator will try to match the right value against any item
in the list and return true if any match.
 
## Available operators

{% for op in rule_operators %}
* `{{ op.name}}` - {{ op.label }}
{% endfor %}


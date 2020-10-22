# Variables

Variables are used in condition expressions and represent information from the evaluated target, usually a pull request.
 
{% include '_implied_triggers.md' %}
 
## Available operators

{% for var in rule_variables %}
* `{{ var.key}}` - {{ var.label }}
{% endfor %}


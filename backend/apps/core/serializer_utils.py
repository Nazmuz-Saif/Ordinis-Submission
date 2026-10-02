def company_of(serializer):
    """The company of the user making the request (None if there is none)."""
    request = serializer.context.get('request')
    return getattr(getattr(request, 'user', None), 'company', None)


def scope_queryset(field, model, company):
    """Limit a related-object field to rows of the user's own company."""
    field.queryset = model.objects.filter(company=company) if company else model.objects.none()

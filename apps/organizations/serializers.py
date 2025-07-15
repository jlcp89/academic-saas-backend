from rest_framework import serializers
from .models import School, Subscription

class SchoolSerializer(serializers.ModelSerializer):
    subscription = serializers.SerializerMethodField()
    
    class Meta:
        model = School
        fields = ['id', 'name', 'subdomain', 'is_active', 'created_at', 'subscription']
        read_only_fields = ['created_at']
    
    def get_subscription(self, obj):
        if hasattr(obj, 'subscription'):
            return SubscriptionSerializer(obj.subscription).data
        return None

class SubscriptionSerializer(serializers.ModelSerializer):
    school_name = serializers.CharField(source='school.name', read_only=True)
    
    class Meta:
        model = Subscription
        fields = ['id', 'school', 'school_name', 'plan', 'status', 'end_date']

class CreateSchoolSerializer(serializers.ModelSerializer):
    subscription_plan = serializers.ChoiceField(choices=Subscription.PlanChoices.choices, write_only=True)
    subscription_end_date = serializers.DateField(write_only=True)
    
    class Meta:
        model = School
        fields = ['name', 'subdomain', 'subscription_plan', 'subscription_end_date']
    
    def create(self, validated_data):
        subscription_plan = validated_data.pop('subscription_plan')
        subscription_end_date = validated_data.pop('subscription_end_date')
        
        school = School.objects.create(**validated_data)
        Subscription.objects.create(
            school=school,
            plan=subscription_plan,
            end_date=subscription_end_date
        )
        return school
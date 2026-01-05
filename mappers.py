from datetime import datetime
from shared.common.constant import InvestorSource
from shared.utils.db_utils import execute_sql_no_return, \
    sql_execute_fetch_one, sql_execute_fetch_all

class PartnerMapper:
    def __init__(self, user_pk=None, user_source_id=None):
        self.user_source_id = user_source_id
        self.user_pk = user_pk

    def partner_list(self):
        detail = sql_execute_fetch_all("select source_name  "
                                       "from lendenapp_source ls ", {})
        return [source['source_name'] for source in detail
                if not source['source_name'] in InvestorSource.INTERNAL_SOURCES]

    def partner_choices(self):
        return tuple([(item, item) for item in self.partner_list()])

    def get_channel_partner_id(self):
        sql = """select id from lendenapp_channelpartner lc 
        where user_id =%(user_pk)s"""
        return sql_execute_fetch_one(sql, {"user_pk": self.user_pk})

    @staticmethod
    def insert_into_legal_auth(**params):
        sql = """
            INSERT INTO public.lendenapp_legal_auth_agreement
            (is_agreeing_to_authorization, is_rbi_investment_compliant, 
            rbi_compliant_date, task_id, created_date, updated_date)
            VALUES(%(is_agreeing_to_authorization)s, 
            %(is_rbi_investment_compliant)s , %(datetime)s, %(task_id)s, 
            %(datetime)s, %(datetime)s )
            """

        params.setdefault("datetime", datetime.now())
        execute_sql_no_return(sql, params)
        
    @staticmethod
    def insert_into_user_terms_conditions(**params):
        sql = """
            INSERT INTO public.lendenapp_usertermsandconditions
            (created_date, updated_date, document_id, user_id, task_id)
            VALUES(%(datetime)s, %(datetime)s, NULL, %(user_pk)s, %(task_id)s)
        """
        params.setdefault("datetime", datetime.now())

        execute_sql_no_return(sql, params)
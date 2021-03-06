from io import StringIO, BytesIO

from flask import Flask, request, send_file, jsonify, abort
from flask_restful import Resource, Api
from pandas import read_sql
from sqlalchemy import create_engine


PARAM_TABLE_MAP = {
    'AGENCY_ID': 'insurance',
    'PRIMARY_AGENCY_ID': 'agency',
    'PROD_ABBR': 'product',
    'PROD_LINE': 'product',
    'STATE_ABBR': 'state',
    'VENDOR': 'vendor',
    'STAT_PROFILE_DATE_YEAR': 'insurance',
    'AGENCY_APPOINTMENT_YEAR': 'insurance',
    'PL_START_YEAR': 'insurance',
    'PL_END_YEAR': 'insurance',
    'COMMISIONS_START_YEAR': 'insurance',
    'COMMISIONS_END_YEAR': 'insurance',
    'CL_START_YEAR': 'insurance',
    'CL_END_YEAR': 'insurance',
    'ACTIVITY_NOTES_START_YEAR': 'insurance',
    'ACTIVITY_NOTES_END_YEAR': 'insurance',
}
JOIN_TEMPLATE = ' INNER JOIN {0} ON {0}.id = insurance.{1}_ID'
WHERE_TEMPLATE = "{}.{} = '{}'"


app = Flask(__name__)
app.debug=True
api = Api(app)


class InvalidParameter(Exception):
    """Return message about invalid parameter."""

    status_code = 422
    message_template = 'Invalid parameter `{}`.'

    def __init__(self, param=None, custom_message_template=None):
        Exception.__init__(self)
        if custom_message_template:
            self.message = custom_message_template.format(param)
        else:
            self.message = self.message_template.format(param)

    def to_dict(self):
        return {'message': self.message}


class MissingParameter(Exception):
    """Return message about missing parameter."""

    status_code = 422
    message_template = 'Missing required parameter `{}`.'

    def __init__(self, param=None, custom_message_template=None):
        Exception.__init__(self)
        if custom_message_template:
            self.message = custom_message_template.format(param)
        else:
            self.message = self.message_template.format(param)

    def to_dict(self):
        return {'message': self.message}


def handle_parameter_exception(error):
    """Handle generic parameter exception in Flask app."""
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


@app.errorhandler(InvalidParameter)
def handle_invalid_parameter(error):
    """Handle InvalidParameter exception in Flask app."""
    return handle_parameter_exception(error)


@app.errorhandler(MissingParameter)
def handle_missing_parameter(error):
    """Handle InvalidParameter exception in Flask app."""
    return handle_parameter_exception(error)


def _select_df(sql, dbapi='sqlite:///insurance.db'):
    """Return pandas.DataFrame of result of SQL query `sql`."""
    con = create_engine(dbapi, echo=False)
    return read_sql(sql, con)


def _sql_response(sql):
    """Return API response based on SQL query `sql`."""
    return _select_df(sql).to_dict(orient='records')
    return {'params': request_args, 'data': data}


def _build_out_sql(sql, request_args):
    """Return modified SQL query `sql` based on request parameters."""
    if bool(request_args):
        joins = set()
        where = []
        for param, value in request_args.items():
            table = PARAM_TABLE_MAP[param]
            if table != 'insurance':
                joins.add(JOIN_TEMPLATE.format(table, table.upper()))
            where.append(WHERE_TEMPLATE.format(table, param, value))
        sql += ''.join(joins)
        sql += ' WHERE {}'.format(' AND '.join(where))
    sql += ';'
    return sql


def _check_params(required_params):
    for param in request.args.keys():
        if param not in PARAM_TABLE_MAP \
        and param not in required_params:
            raise InvalidParameter(param)
    for param in required_params:
        if param not in request.args.keys():
            raise MissingParameter(param)


class Details(Resource):
    """Return detailed information using different parameters."""

    required_params = ['AGENCY_ID', 'PROD_LINE']
    
    def get(self):
        _check_params(self.required_params)

        sql = 'SELECT insurance.* FROM insurance'
        sql = _build_out_sql(sql, request.args)
        return _sql_response(sql)


class Summary(Resource):
    """Return summarized information using different parameters."""

    required_params = ['AGG']

    def get(self):
        _check_params(self.required_params)

        sql = '''SELECT
            COUNT(*) AS RESULTS_COUNT,
            '{0}' AS AGG,
            {0}(RETENTION_POLY_QTY) AS RETENTION_POLY_QTY,
            {0}(POLY_INFORCE_QTY) AS POLY_INFORCE_QTY,
            {0}(PREV_POLY_INFORCE_QTY) AS PREV_POLY_INFORCE_QTY,
            {0}(NB_WRTN_PREM_AMT) AS NB_WRTN_PREM_AMT,
            {0}(WRTN_PREM_AMT) AS WRTN_PREM_AMT,
            {0}(PREV_WRTN_PREM_AMT) AS PREV_WRTN_PREM_AMT,
            {0}(PRD_ERND_PREM_AMT) AS PRD_ERND_PREM_AMT,
            {0}(PRD_INCRD_LOSSES_AMT) AS PRD_INCRD_LOSSES_AMT,
            {0}(RETENTION_RATIO) AS RETENTION_RATIO,
            {0}(LOSS_RATIO) AS LOSS_RATIO,
            {0}(LOSS_RATIO_3YR) AS LOSS_RATIO_3YR,
            {0}(GROWTH_RATE_3YR) AS GROWTH_RATE_3YR,
            {0}(CL_BOUND_CT_MDS) AS CL_BOUND_CT_MDS,
            {0}(CL_QUO_CT_MDS) AS CL_QUO_CT_MDS,
            {0}(CL_BOUND_CT_SBZ) AS CL_BOUND_CT_SBZ,
            {0}(CL_QUO_CT_SBZ) AS CL_QUO_CT_SBZ,
            {0}(CL_QUO_CT_EQT) AS CL_QUO_CT_EQT,
            {0}(PL_BOUND_CT_ELINKS) AS PL_BOUND_CT_ELINKS,
            {0}(PL_QUO_CT_ELINKS) AS PL_QUO_CT_ELINKS,
            {0}(PL_BOUND_CT_PLRANK) AS PL_BOUND_CT_PLRANK,
            {0}(PL_QUO_CT_PLRANK) AS PL_QUO_CT_PLRANK,
            {0}(PL_BOUND_CT_EQTTE) AS PL_BOUND_CT_EQTTE,
            {0}(PL_QUO_CT_EQTTE) AS PL_QUO_CT_EQTTE,
            {0}(PL_BOUND_CT_APPLIED) AS PL_BOUND_CT_APPLIED,
            {0}(PL_QUO_CT_APPLIED) AS PL_QUO_CT_APPLIED,
            {0}(PL_BOUND_CT_TRANSACTNOW) AS PL_BOUND_CT_TRANSACTNOW,
            {0}(PL_QUO_CT_TRANSACTNOW) AS PL_QUO_CT_TRANSACTNOW
        FROM INSURANCE'''.format(request.args['AGG'])
        args = dict(request.args.items())
        for i in self.required_params:
            del args[i]
        sql = _build_out_sql(sql, args)
        print(sql)
        return _sql_response(sql)


class Report(Resource):
    """Return a CSV report with Premium info by Agency and Product Line
    using date range as parameters.

    Date range is inclusive, using PL_START_YEAR and PL_END_YEAR.
    """

    def get(self):
        sql = '''SELECT
            i.AGENCY_ID AS AGENCY_ID,
            p.PROD_LINE AS PROD_LINE,
            SUM(i.NB_WRTN_PREM_AMT) AS NB_WRTN_PREM_AMT_SUM,
            SUM(i.WRTN_PREM_AMT) AS WRTN_PREM_AMT_SUM,
            SUM(i.PREV_WRTN_PREM_AMT) AS PREV_WRTN_PREM_AMT_SUM,
            SUM(i.PRD_ERND_PREM_AMT) AS PRD_ERND_PREM_AMT_SUM
        FROM insurance i
        INNER JOIN product p ON p.id = i.PRODUCT_ID
        '''
        if bool(request.args):
            where = []
            for param, value in request.args.items():
                if param not in ['MIN_PL_START_YEAR', 'MAX_PL_START_YEAR',
                                 'MIN_PL_END_YEAR', 'MAX_PL_END_YEAR']:
                    raise InvalidParameter(param)
                elif len(value) == 4 and value.isdigit():
                    if param.startswith('MIN'):
                        operator = '>'
                    else:
                        operator = '<'
                    where.append('i.{} {}= {}'.format(
                        param[4:], operator, value
                        ))
                else:
                    message = '{} must follow the format YYYY'
                    raise InvalidParameter(param, message)
            sql += ' WHERE {}'.format(' AND '.join(where))
        sql += ' GROUP BY i.AGENCY_ID, p.PROD_LINE;'

        df = _select_df(sql)
        s = StringIO()
        df.to_csv(s, index=False)
        b = BytesIO()
        b.write(s.getvalue().encode('utf-8'))
        s.close()
        b.seek(0)
        return send_file(b, mimetype = 'text/csv', as_attachment=True, 
                         attachment_filename='report.csv')


api.add_resource(Details, '/details')
api.add_resource(Summary, '/summary')
api.add_resource(Report, '/report')


if __name__ == '__main__':
    app.run()
# -*- coding: utf-8 -*-

import logging

from django.utils.encoding import smart_str
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from pyquery import PyQuery as pq

from common import debug
from common.alipay import alipay_mobile
from common.weixinpay.weixinpay import Weixinpay
from www.car_wash.interface import OrderBase
from www.cash.interface import CashOrderBase


def alipaycallback_m(request):
    """
    @note: 支付宝手机支付回调，页面跳转方式
    仅做检测，不做后续处理，由服务器通知方式进行后续处理，避免同时并发的方式
    """
    logging.error(u"alipaycallback_m info is: %s" % request.REQUEST)

    alipay = alipay_mobile.Alipay()
    flag = alipay.validate_html_redirect_params(request)
    if flag:
        timeinterval = 3
        next_url = "/car_wash/"  # 成功跳转url控制
        if request.REQUEST.get("out_trade_no", "").startswith("W"):
            next_url = "/car_wash/order_code"
        if request.REQUEST.get("out_trade_no", "").startswith("R"):
            next_url = "/cash"

        success_msg = u'支付成功，页面即将跳转'
        return render_to_response('success.html', locals(), context_instance=RequestContext(request))
    else:
        err_msg = u'支付结果校验异常，请联系车咖客服人员'
        return render_to_response('error.html', locals(), context_instance=RequestContext(request))


def alipaynotify_m(request):
    """
    @note: 支付宝手机支付通知，服务器通知方式
    """
    logging.error(u"alipaynotify_m info is: %s" % request.REQUEST)

    alipay = alipay_mobile.Alipay()
    flag = alipay.validate_notify_params(request)
    result = 'fail'
    if flag:
        notify_data = request.REQUEST.get('notify_data', '')
        jq = pq(notify_data)
        trade_status = jq('trade_status').html()

        if trade_status in ('TRADE_FINISHED', 'TRADE_SUCCESS'):
            trade_no = jq('trade_no').html()
            buyer_email = jq('buyer_email').html()
            buyer_id = jq('buyer_id').html()
            trade_id = jq('out_trade_no').html()
            total_fee = float(jq('total_fee').html())
            pay_info = 'trade_no:%s, buyer_email:%s, buyer_id:%s' % (trade_no, buyer_email, buyer_id)

            if trade_id.startswith("W"):
                errcode, errmsg = OrderBase().order_pay_callback(trade_id=trade_id, payed_fee=total_fee, pay_info=pay_info)
            elif trade_id.startswith("R"):
                errcode, errmsg = CashOrderBase().cash_order_pay_callback(trade_id=trade_id, payed_fee=total_fee, pay_info=pay_info)
            result = u'success' if errcode in (0, 20301) else 'fail'  # 不存在的订单返回成功防止一直补发

    return HttpResponse(result)


def weixinnotify(request):
    """
    @note: 微信支付回调服务通知接口
    """
    xml_data = request.read()
    logging.error(u"weixinnotify info is: %s" % xml_data)

    weixinpay = Weixinpay()
    result = 'FAIL'
    errmsg = "OK"

    params = weixinpay.format_xml_data_to_params(xml_data)

    # 先判断协议返回错误码, 再判断业务返回错误码
    if params.get("return_code") == "SUCCESS" and params.get("result_code") == "SUCCESS":
        flag = weixinpay.validate_notify_params(params)
        if flag:
            trade_no = params.get("transaction_id")
            appid = params.get("appid")
            buyer_id = params.get("openid")
            trade_id = params.get("out_trade_no")
            total_fee = float(params.get('total_fee')) / 100.0    # 微信金额以分为单位
            pay_info = 'trade_no:%s, appid:%s, buyer_id:%s' % (trade_no, appid, buyer_id)

            if trade_id.startswith("W"):
                errcode, errmsg = OrderBase().order_pay_callback(trade_id=trade_id, payed_fee=total_fee, pay_info=pay_info)
            elif trade_id.startswith("R"):
                errcode, errmsg = CashOrderBase().cash_order_pay_callback(trade_id=trade_id, payed_fee=total_fee, pay_info=pay_info)
            result = u'SUCCESS' if errcode in (0, 20301) else 'FAIL'  # 不存在的订单返回成功防止一直补发

    xml = u"<xml><return_code><![CDATA[%s]]></return_code><return_msg><![CDATA[%s]]></return_msg></xml>" % (result, errmsg)
    logging.error(u"weixinnotify return is: %s" % xml)
    return HttpResponse(xml, mimetype='text/xml')


def weixin_success_info(request):
    """
    @note: 微信支付成功后页面页面提示
    """
    timeinterval = 3
    next_url = "/car_wash/"  # 成功跳转url控制
    if request.REQUEST.get("out_trade_no", "").startswith("W"):
        next_url = "/car_wash/order_code"
    if request.REQUEST.get("out_trade_no", "").startswith("R"):
        next_url = "/cash"

    success_msg = u'微信支付成功，页面即将跳转'
    return render_to_response('success.html', locals(), context_instance=RequestContext(request))


def weixinwarning(request):
    """
    @note: 微信支付告警通知接口, 微信监测到商户服务出现问题时，会及时推送相关告警信息到商户后台
    """
    from django.conf import settings
    from www.tasks import async_send_email

    if request.GET or request.POST:
        title = u'微信支付告警通知'
        content = u'告警内容如下：\n%s' % request.REQUEST
        async_send_email(settings.NOTIFICATION_EMAIL, title, content)
    return HttpResponse("ok")


def test_paycallback(request):
    """
    @note: 测试回调
    """
    params = request.REQUEST

    if request.user.id in (u'd081652b603211e48a41685b35d0bf16',):
        buyer_email = params.get('buyer_email')
        buyer_id = params.get('buyer_id')
        trade_no = params.get('trade_no')
        trade_id = params.get('out_trade_no')
        total_fee = float(params.get('total_fee'))

        errcode, errmsg = 0, "支付成功"
        try:
            ob = OrderBase()
            pay_info = 'trade_no:%s, buyer_email:%s, buyer_id:%s' % (trade_no, buyer_email, buyer_id)

            if trade_id.startswith("W"):
                errcode, errmsg = ob.order_pay_callback(trade_id=trade_id, payed_fee=total_fee, pay_info=pay_info)
            elif trade_id.startswith("R"):
                errcode, errmsg = CashOrderBase().cash_order_pay_callback(trade_id=trade_id, payed_fee=total_fee, pay_info=pay_info)

            status = u'success' if errcode == 0 else 'fail'
        except Exception, e:
            debug.get_debug_detail(e)
            status = u'fail'
            errmsg = u'支付遇到问题: %s' % str(e)

        if errcode == 20301:    # 不存在的订单返回成功防止一直补发
            return HttpResponse('success')

        return HttpResponse(u"status is:%s\nerrmsg is:%s" % (status, errmsg))
    return HttpResponse("not the one who can test")

# -*- coding: utf-8 -*-


def wind_convert_to_data_yes(wind_sec_id):
    """
    :param wind_sec_id: single str or list wind sec id, i.e. 000300.SH/000300.sh
    :return: datayes type code, 1.e. 000300.xshg
    """

    def replace_suffix(sec_ids):
        sec_id_comp = sec_ids.split('.')
        if sec_id_comp[1] == 'sh':
            data_yes_id = sec_id_comp[0] + '.xshg'
        elif sec_id_comp[1] == 'sz':
            data_yes_id = sec_id_comp[0] + '.xshe'
        else:
            raise ValueError("Unknown securities name {0}. Security names without"
                             " exchange suffix is not allowed".format(s))
        return data_yes_id

    if isinstance(wind_sec_id, list):
        wind_sec_id_list = [s.lower() for s in wind_sec_id]
        ret = [replace_suffix(s) for s in wind_sec_id_list]
    else:
        ret = replace_suffix(wind_sec_id.lower())

    return ret


def data_yes_convert_to_wind(data_yes_id):
    """
    :param data_yes_id: list, datayes type code, 1.e. 000300.xshg
    :return: list, wind sec id, i.e. 000300.SH/000300.sh
    """

    # TODO how to deal with index id?

    def replace_suffix(data_yes_ids):
        sec_id_comp = data_yes_ids.split('.')
        if sec_id_comp[1] == 'xshg':
            wind_sec_id = sec_id_comp[0] + '.sh'
        elif sec_id_comp[1] == 'xshe':
            wind_sec_id = sec_id_comp[0] + '.sz'
        else:
            raise ValueError("Unknown securities name {0}. Security names without"
                             " exchange suffix is not allowed".format(s))
        return wind_sec_id

    if isinstance(data_yes_id, list):
        data_yes_id_list = [s.lower() for s in data_yes_id]
        ret = [replace_suffix(s) for s in data_yes_id_list]
    else:
        ret = replace_suffix(data_yes_id.lower())

    return ret


def remove_suffix(sec_ids):
    """
    :param sec_ids: list wind or datayes sec id, i.e. 000300.SH/000300.xshg
    :return: code without suffix, 1.e. 000300
    """

    if isinstance(sec_ids, list):
        ret = [s.split('.')[0] for s in sec_ids]
    else:
        ret = sec_ids.split('.')[0]

    return ret

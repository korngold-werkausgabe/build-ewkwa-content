<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:edirom="http://www.edirom.de/ns/1.3" 
    xmlns="http://www.edirom.de/ns/1.3"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform" 
    version="1.0">

    <xsl:output indent="yes" />
    <xsl:param name="subDiv"></xsl:param>
    <xsl:param name="volSlug"></xsl:param>
    
    <xsl:template match="@*|text()">
        <xsl:copy/>
    </xsl:template>
    
    <xsl:template match="processing-instruction()"/>
    
    <xsl:template match="*">
        <xsl:element name="{local-name()}" namespace="http://www.edirom.de/ns/1.3">
            <xsl:apply-templates select="@*[name() != 'xml:id' and name() != 'sortNo']|node()"/>
        </xsl:element>
    </xsl:template>
    
    <xsl:template match="navigatorDefinition">
        <navigatorDefinition>
            <xsl:attribute name="xml:id">
            <xsl:choose>
                <xsl:when test="$subDiv and $subDiv != '' and $subDiv != 'None'">
                    <xsl:value-of select="concat($subDiv, '_navDef')"/>
                </xsl:when>
                <xsl:otherwise>
                    <xsl:value-of select="'navDef'"/>
                </xsl:otherwise>
            </xsl:choose>
            </xsl:attribute>
            <xsl:apply-templates select="@*[name() != 'xml:id']|node()"/>
        </navigatorDefinition>
    </xsl:template>
    
    <xsl:template match="navigatorCategory">
        <xsl:variable name="genId" select="generate-id()"/>
        <navigatorCategory>
            <xsl:attribute name="xml:id">
            <xsl:choose>
                <xsl:when test="$subDiv and $subDiv != '' and $subDiv != 'None'">
                    <xsl:value-of select="concat($subDiv, '_', $genId)"/>
                </xsl:when>
                <xsl:otherwise>
                    <xsl:value-of select="$genId"/>
                </xsl:otherwise>
            </xsl:choose>
            </xsl:attribute>
            <xsl:apply-templates select="@*[name() != 'xml:id' and name() != 'sortNo']|node()"/>
        </navigatorCategory>
    </xsl:template>
    
    <xsl:template match="navigatorItem">
        <xsl:variable name="itemPos" select="count(preceding-sibling::navigatorItem) + 1"/>
        <xsl:variable name="parentCatId" select="ancestor::navigatorCategory[1]/@xml:id"/>
        <navigatorItem>
            <xsl:attribute name="xml:id">
            <xsl:choose>
                <xsl:when test="$subDiv and $subDiv != '' and $subDiv != 'None'">
                    <xsl:value-of select="concat($subDiv, '_item_', generate-id())"/>
                </xsl:when>
                <xsl:otherwise>
                    <xsl:value-of select="concat('item_', generate-id())"/>
                </xsl:otherwise>
            </xsl:choose>
            </xsl:attribute>
            <xsl:attribute name="sortNo"><xsl:value-of select="$itemPos"/></xsl:attribute>
            <xsl:attribute name="targets">  
                <xsl:text>xmldb:exist:///db/apps/edirom-content/</xsl:text>  
                <xsl:value-of select="$volSlug"/>
                <xsl:text>/</xsl:text>  
                <xsl:choose>
                    <xsl:when test="$subDiv and $subDiv != '' and $subDiv != 'None'">
                        <xsl:value-of select="$parentCatId"/>
                    </xsl:when>
                    <xsl:otherwise/>
                </xsl:choose>
                <xsl:value-of select="@targets"/>
            </xsl:attribute>
            <xsl:apply-templates select="@*[name() != 'targets']|node()"/>
        </navigatorItem>
    </xsl:template>
    
</xsl:stylesheet>